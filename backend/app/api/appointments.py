"""
预约信息管理API路由
处理用户端预约提交和管理端数据导出/统计功能
"""
import csv
import io
from datetime import date, time, datetime
from pathlib import Path
from typing import Dict, List, Any
from filelock import FileLock
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, constr
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.deps import get_current_active_user
from ..db.session import get_db
from ..models.user import User

# 创建路由器
router = APIRouter(tags=["Appointments"])


class BookingIn(BaseModel):
    """用户预约信息输入模型"""
    name: constr(strip_whitespace=True, min_length=1, max_length=50)
    phone: constr(strip_whitespace=True, min_length=5, max_length=30) 
    address: constr(strip_whitespace=True, min_length=1, max_length=200)
    date: date  # 预约日期，格式 YYYY-MM-DD
    time: time  # 预约时间，格式 HH:MM
    issue: constr(strip_whitespace=True, min_length=1, max_length=500)


class BookingResponse(BaseModel):
    """预约提交响应模型"""
    success: bool
    message: str
    booking_id: str = None


class AppointmentStats(BaseModel):
    """预约统计模型"""
    total_appointments: int
    appointments_by_date: Dict[str, int]
    recent_appointments: List[Dict[str, Any]]


def escape_csv_injection(value: str) -> str:
    """
    防止CSV注入攻击
    对以 =, +, -, @, \t 开头的字符串进行转义
    """
    if not isinstance(value, str):
        return str(value)
    
    dangerous_chars = ['=', '+', '-', '@', '\t']
    if value and value[0] in dangerous_chars:
        return "'" + value
    return value


def write_to_csv(booking_data: BookingIn) -> str:
    """
    将预约信息写入CSV文件
    使用文件锁确保并发安全
    返回booking_id
    """
    csv_path = settings.appointments_csv
    lock_path = str(csv_path) + ".lock"
    
    # 生成booking_id
    booking_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 准备CSV行数据
    row_data = [
        booking_id,
        escape_csv_injection(booking_data.name),
        escape_csv_injection(booking_data.phone),
        escape_csv_injection(booking_data.address),
        booking_data.date.strftime('%Y-%m-%d'),
        booking_data.time.strftime('%H:%M'),
        escape_csv_injection(booking_data.issue),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 提交时间
    ]
    
    # 使用文件锁确保并发安全
    with FileLock(lock_path):
        file_exists = csv_path.exists()
        
        # 以UTF-8 BOM编码写入（Excel友好）
        with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 如果文件不存在，写入表头
            if not file_exists:
                headers = [
                    '预约编号', '姓名', '联系电话', '地址', 
                    '预约日期', '预约时间', '问题描述', '提交时间'
                ]
                writer.writerow(headers)
            
            # 写入数据行
            writer.writerow(row_data)
    
    return booking_id


@router.post("/public/booking", response_model=BookingResponse)
async def submit_booking(booking: BookingIn, db: Session = Depends(get_db)):
    """
    用户端预约提交接口（公开接口，无需认证）
    现在创建工单而不是写入CSV
    """
    try:
        # Import here to avoid circular imports
        from ..models.ticket import Ticket, TicketCreate
        from ..services.tickets_service import TicketsService
        import hashlib
        
        # Hash phone for privacy
        phone_hash = hashlib.sha256(booking.phone.encode()).hexdigest()
        
        # Create ticket
        ticket = Ticket(
            customer_name=booking.name,
            customer_phone_hash=phone_hash,
            address=booking.address,
            appointment_date=booking.date,
            appointment_time=booking.time,
            issue_desc=booking.issue
        )
        db.add(ticket)
        
        # Create service and event
        tickets_service = TicketsService(db)
        tickets_service.create_ticket_event(
            ticket.id, 
            "CONFIRM", 
            details={"source": "public_booking"}
        )
        
        db.commit()
        
        # Also write to CSV for backward compatibility
        booking_id = write_to_csv(booking)
        
        return BookingResponse(
            success=True,
            message="预约提交成功！我们会尽快联系您。",
            booking_id=f"TK{str(ticket.id)[:8]}"  # 显示工单短ID
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预约提交失败：{str(e)}"
        )


@router.get("/admin/appointments/download")
async def download_appointments_csv(
    current_user: User = Depends(get_current_active_user)
):
    """
    管理端下载预约数据CSV文件
    需要管理员权限
    """
    csv_path = settings.appointments_csv
    
    if not csv_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无预约数据"
        )
    
    def iter_csv():
        with open(csv_path, 'rb') as f:
            yield from f
    
    filename = f"appointments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/admin/appointments/stats", response_model=AppointmentStats)
async def get_appointments_stats(
    current_user: User = Depends(get_current_active_user)
):
    """
    管理端获取预约统计信息
    需要管理员权限
    """
    csv_path = settings.appointments_csv
    
    if not csv_path.exists():
        return AppointmentStats(
            total_appointments=0,
            appointments_by_date={},
            recent_appointments=[]
        )
    
    appointments_by_date = {}
    recent_appointments = []
    total_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            total_count = len(rows)
            
            # 按预约日期统计
            for row in rows:
                appointment_date = row.get('预约日期', '')
                if appointment_date:
                    appointments_by_date[appointment_date] = appointments_by_date.get(appointment_date, 0) + 1
            
            # 获取最近的10条预约记录
            recent_appointments = [
                {
                    'booking_id': row.get('预约编号', ''),
                    'name': row.get('姓名', ''),
                    'phone': row.get('联系电话', ''),
                    'date': row.get('预约日期', ''),
                    'time': row.get('预约时间', ''),
                    'submit_time': row.get('提交时间', '')
                }
                for row in rows[-10:]  # 最后10条记录
            ]
            recent_appointments.reverse()  # 最新的在前
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取预约数据失败：{str(e)}"
        )
    
    return AppointmentStats(
        total_appointments=total_count,
        appointments_by_date=appointments_by_date,
        recent_appointments=recent_appointments
    ) 