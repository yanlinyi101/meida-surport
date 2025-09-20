"""
Seed script for tickets system test data.
"""
import sys
import os
from datetime import datetime, date, time, timedelta
from uuid import uuid4

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.technician import Technician
from app.models.ticket import Ticket, TicketStatus
from app.services.tickets_service import TicketsService
import hashlib


def create_test_technicians(db):
    """Create test technicians."""
    technicians = [
        {
            "name": "张师傅",
            "phone_masked": "138****1234",
            "center_id": None,
            "skills": '["燃气灶维修", "油烟机清洗", "热水器安装"]',
            "is_active": True
        },
        {
            "name": "李师傅", 
            "phone_masked": "139****5678",
            "center_id": None,
            "skills": '["消毒柜维修", "洗碗机安装", "集成灶维修"]',
            "is_active": True
        },
        {
            "name": "王师傅",
            "phone_masked": "136****9012", 
            "center_id": None,
            "skills": '["燃气灶维修", "热水器维修", "油烟机维修"]',
            "is_active": True
        }
    ]
    
    created_technicians = []
    for tech_data in technicians:
        # Check if technician already exists
        existing = db.query(Technician).filter(
            Technician.name == tech_data["name"]
        ).first()
        
        if not existing:
            technician = Technician(**tech_data)
            db.add(technician)
            created_technicians.append(technician)
            print(f"Created technician: {tech_data['name']}")
        else:
            created_technicians.append(existing)
            print(f"Technician already exists: {tech_data['name']}")
    
    db.commit()
    return created_technicians


def create_test_tickets(db, technicians):
    """Create test tickets."""
    tickets_service = TicketsService(db)
    
    # Sample ticket data
    base_date = datetime.now().date()
    tickets_data = [
        {
            "customer_name": "陈女士",
            "phone": "13812345678",
            "address": "上海市浦东新区张江高科技园区祖冲之路899号",
            "appointment_date": base_date + timedelta(days=1),
            "appointment_time": time(9, 0),
            "issue_desc": "燃气灶点火困难，需要检查点火器",
            "status": TicketStatus.BOOKED
        },
        {
            "customer_name": "刘先生", 
            "phone": "13987654321",
            "address": "北京市朝阳区建国门外大街1号国贸大厦",
            "appointment_date": base_date + timedelta(days=2),
            "appointment_time": time(14, 30),
            "issue_desc": "油烟机噪音很大，需要清洗和检修",
            "status": TicketStatus.CONFIRMED
        },
        {
            "customer_name": "王女士",
            "phone": "13611112222", 
            "address": "广州市天河区珠江新城花城大道85号",
            "appointment_date": base_date,
            "appointment_time": time(10, 0),
            "issue_desc": "热水器不出热水，显示错误代码E1",
            "status": TicketStatus.ASSIGNED
        },
        {
            "customer_name": "张先生",
            "phone": "13733334444",
            "address": "深圳市南山区科技园南区高新南一道009号",
            "appointment_date": base_date - timedelta(days=1),
            "appointment_time": time(16, 0),
            "issue_desc": "消毒柜门关不严，内部灯不亮",
            "status": TicketStatus.IN_PROGRESS
        },
        {
            "customer_name": "赵女士",
            "phone": "13555556666",
            "address": "杭州市西湖区文三路259号昌地火炬大厦",
            "appointment_date": base_date - timedelta(days=3),
            "appointment_time": time(11, 30),
            "issue_desc": "集成灶左侧炉头无法点火，需要更换点火针",
            "status": TicketStatus.COMPLETED
        }
    ]
    
    created_tickets = []
    for i, ticket_data in enumerate(tickets_data):
        # Hash phone for privacy
        phone_hash = hashlib.sha256(ticket_data["phone"].encode()).hexdigest()
        
        # Check if ticket already exists (by customer name and date)
        existing = db.query(Ticket).filter(
            Ticket.customer_name == ticket_data["customer_name"],
            Ticket.appointment_date == ticket_data["appointment_date"]
        ).first()
        
        if not existing:
            ticket = Ticket(
                customer_name=ticket_data["customer_name"],
                customer_phone_hash=phone_hash,
                address=ticket_data["address"],
                appointment_date=ticket_data["appointment_date"],
                appointment_time=ticket_data["appointment_time"],
                issue_desc=ticket_data["issue_desc"],
                status=ticket_data["status"]
            )
            
            # Assign technicians to some tickets
            if ticket_data["status"] in [TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.COMPLETED]:
                ticket.technician_id = technicians[i % len(technicians)].id
            
            # Set completion time for completed tickets
            if ticket_data["status"] == TicketStatus.COMPLETED:
                ticket.completed_at = datetime.now() - timedelta(hours=2)
            
            db.add(ticket)
            created_tickets.append(ticket)
            
            db.commit()  # Commit first to ensure ticket.id is available
            
            # Create events for tickets
            if ticket_data["status"] != TicketStatus.BOOKED:
                tickets_service.create_ticket_event(
                    ticket.id,
                    "CONFIRM",
                    details={"source": "seed_script"}
                )
            
            if ticket_data["status"] in [TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.COMPLETED]:
                tickets_service.create_ticket_event(
                    ticket.id,
                    "ASSIGN", 
                    details={
                        "technician_id": str(ticket.technician_id),
                        "technician_name": next(t.name for t in technicians if t.id == ticket.technician_id),
                        "assignment_method": "manual"
                    }
                )
            
            if ticket_data["status"] in [TicketStatus.IN_PROGRESS, TicketStatus.COMPLETED]:
                tickets_service.create_ticket_event(
                    ticket.id,
                    "STATUS_CHANGE",
                    details={"old_status": "ASSIGNED", "new_status": "IN_PROGRESS"}
                )
            
            if ticket_data["status"] == TicketStatus.COMPLETED:
                tickets_service.create_ticket_event(
                    ticket.id,
                    "UPLOAD_RECEIPT",
                    details={"image_id": str(uuid4()), "filename": "receipt_sample.jpg"}
                )
                tickets_service.create_ticket_event(
                    ticket.id,
                    "COMPLETE",
                    details={"completed_at": ticket.completed_at.isoformat()}
                )
            
            print(f"Created ticket: {ticket_data['customer_name']} - {ticket_data['status'].value}")
        else:
            created_tickets.append(existing)
            print(f"Ticket already exists: {ticket_data['customer_name']}")
    
    db.commit()  # Final commit for any remaining events
    return created_tickets


def main():
    """Main seed function."""
    print("🌱 Seeding tickets system test data...")
    
    db = SessionLocal()
    try:
        # Create test technicians
        print("\n📋 Creating test technicians...")
        technicians = create_test_technicians(db)
        
        # Create test tickets
        print("\n🎫 Creating test tickets...")
        tickets = create_test_tickets(db, technicians)
        
        print(f"\n✅ Seed completed successfully!")
        print(f"   - Created/Found {len(technicians)} technicians")
        print(f"   - Created/Found {len(tickets)} tickets")
        print(f"\n💡 You can now:")
        print(f"   - View tickets at: http://localhost:8000/admin/tickets")
        print(f"   - View technician jobs at: http://localhost:8000/admin/my-jobs")
        
    except Exception as e:
        print(f"❌ Seed failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main() 