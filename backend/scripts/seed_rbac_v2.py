"""
RBAC v2 种子脚本 - 初始化权限、角色和系统数据
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy.orm import sessionmaker
from backend.app.db.base import Base, engine
from backend.app.models.user import User
from backend.app.models.role import Role, Permission
from backend.app.core.security import hash_password
from backend.app.services.rbac_service import PERMISSIONS, SYSTEM_ROLE_CORE_PERMISSIONS

# Import all models to ensure they are registered
from backend.app.models import user, role, session, audit

def init_permissions(db):
    """初始化权限数据"""
    print("🔐 初始化权限数据...")
    
    created_count = 0
    updated_count = 0
    
    for category, permission_codes in PERMISSIONS.items():
        for code in permission_codes:
            existing_perm = db.query(Permission).filter(Permission.code == code).first()
            
            if not existing_perm:
                # Create new permission
                description = generate_permission_description(code)
                permission = Permission(
                    code=code,
                    description=description,
                    category=category
                )
                db.add(permission)
                created_count += 1
                print(f"  ➕ 创建权限: {code} ({category})")
            else:
                # Update category if different
                if existing_perm.category != category:
                    existing_perm.category = category
                    updated_count += 1
                    print(f"  🔄 更新权限分类: {code} -> {category}")
    
    db.commit()
    print(f"✅ 权限初始化完成: 创建 {created_count} 个, 更新 {updated_count} 个")
    return created_count + updated_count

def generate_permission_description(code: str) -> str:
    """生成权限描述"""
    descriptions = {
        "users.read": "查看用户信息",
        "users.write": "创建和编辑用户",
        "roles.read": "查看角色信息", 
        "roles.write": "创建和编辑角色",
        "permissions.read": "查看权限信息",
        "audit.read": "查看审计日志",
        "tickets.read": "查看工单信息",
        "tickets.write": "创建和编辑工单",
        "warranty.read": "查看保修信息",
        "warranty.reindex": "重建保修索引",
        "centers.write": "管理服务中心信息",
        "ai.workflow.run": "运行AI工作流",
        "ai.chat": "使用AI聊天功能",
        "geo.read": "查看地理位置信息",
        "system.admin": "系统管理权限"
    }
    return descriptions.get(code, f"权限: {code}")

def init_system_roles(db):
    """初始化系统角色"""
    print("👑 初始化系统角色...")
    
    role_definitions = {
        "admin": {
            "description": "系统管理员 - 拥有所有权限",
            "permissions": SYSTEM_ROLE_CORE_PERMISSIONS["admin"]
        },
        "agent": {
            "description": "客服代理 - 处理工单和保修查询",
            "permissions": SYSTEM_ROLE_CORE_PERMISSIONS["agent"]
        },
        "viewer": {
            "description": "只读用户 - 仅查看权限",
            "permissions": SYSTEM_ROLE_CORE_PERMISSIONS["viewer"]
        },
        "ops_manager": {
            "description": "运营经理 - 用户管理和运营权限",
            "permissions": SYSTEM_ROLE_CORE_PERMISSIONS["ops_manager"]
        }
    }
    
    created_count = 0
    updated_count = 0
    
    for role_name, role_info in role_definitions.items():
        existing_role = db.query(Role).filter(Role.name == role_name).first()
        
        if not existing_role:
            # Create new system role
            role = Role(
                name=role_name,
                description=role_info["description"],
                is_system=True
            )
            db.add(role)
            db.flush()  # Get the role ID
            created_count += 1
            print(f"  ➕ 创建系统角色: {role_name}")
        else:
            role = existing_role
            # Update description and ensure it's marked as system role
            if role.description != role_info["description"]:
                role.description = role_info["description"]
                updated_count += 1
            if not role.is_system:
                role.is_system = True
                updated_count += 1
        
        # Assign permissions to role
        permission_objects = db.query(Permission).filter(
            Permission.code.in_(role_info["permissions"])
        ).all()
        
        current_permission_codes = {p.code for p in role.permissions}
        new_permission_codes = set(role_info["permissions"])
        
        if current_permission_codes != new_permission_codes:
            role.permissions = permission_objects
            print(f"  🔄 更新 {role_name} 角色权限: {len(permission_objects)} 个权限")
    
    db.commit()
    print(f"✅ 系统角色初始化完成: 创建 {created_count} 个, 更新 {updated_count} 个")
    return created_count + updated_count

def ensure_admin_user(db):
    """确保存在管理员用户"""
    print("👤 检查管理员用户...")
    
    admin_email = "admin@meidasupport.com"
    admin_user = db.query(User).filter(User.email == admin_email).first()
    
    if not admin_user:
        # Create admin user
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("❌ 错误: admin角色不存在，请先运行角色初始化")
            return False
        
        admin_user = User(
            email=admin_email,
            password_hash=hash_password("admin123456"),
            display_name="系统管理员",
            is_active=True
        )
        admin_user.roles = [admin_role]
        db.add(admin_user)
        db.commit()
        
        print(f"  ➕ 创建管理员用户: {admin_email}")
        print("  🔑 默认密码: admin123456")
        print("  ⚠️  请首次登录后立即修改密码！")
        return True
    else:
        # Ensure admin user has admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
            db.commit()
            print(f"  🔄 为管理员用户添加admin角色")
        
        print(f"  ✅ 管理员用户已存在: {admin_email}")
        return True

def print_summary(db):
    """打印初始化摘要"""
    print("\n📊 RBAC v2 系统摘要:")
    
    # Count permissions by category
    permission_stats = db.query(Permission.category, db.func.count(Permission.id))\
        .group_by(Permission.category).all()
    
    print("  权限统计:")
    total_permissions = 0
    for category, count in permission_stats:
        print(f"    {category}: {count} 个权限")
        total_permissions += count
    print(f"    总计: {total_permissions} 个权限")
    
    # Count roles
    total_roles = db.query(Role).count()
    system_roles = db.query(Role).filter(Role.is_system == True).count()
    custom_roles = total_roles - system_roles
    
    print(f"  角色统计:")
    print(f"    系统角色: {system_roles} 个")
    print(f"    自定义角色: {custom_roles} 个")
    print(f"    总计: {total_roles} 个角色")
    
    # Count users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    print(f"  用户统计:")
    print(f"    活跃用户: {active_users} 个")
    print(f"    总用户: {total_users} 个")

def main():
    """主函数"""
    print("🚀 开始 RBAC v2 数据初始化...")
    
    try:
        # Create tables if they don't exist
        print("📋 创建数据表...")
        Base.metadata.create_all(bind=engine)
        
        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Initialize permissions
            perm_changes = init_permissions(db)
            
            # Initialize system roles
            role_changes = init_system_roles(db)
            
            # Ensure admin user exists
            admin_created = ensure_admin_user(db)
            
            # Print summary
            print_summary(db)
            
            print(f"\n🎉 RBAC v2 初始化完成!")
            print(f"   权限变更: {perm_changes}")
            print(f"   角色变更: {role_changes}")
            print(f"   管理员: {'已创建' if admin_created else '已存在'}")
            
        except Exception as e:
            print(f"❌ 初始化过程中出错: {e}")
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 