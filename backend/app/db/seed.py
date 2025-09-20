"""
Database seed script for initializing roles, permissions, and admin user.
"""
from sqlalchemy.orm import Session
from ..models.user import User
from ..models.role import Role, Permission
from ..core.security import hash_password
from .session import SessionLocal


def create_permissions(db: Session) -> dict[str, Permission]:
    """Create default permissions."""
    permissions_data = [
        # User management
        ("users.read", "查看用户信息"),
        ("users.write", "创建和编辑用户"),
        ("users.delete", "删除用户"),
        
        # Role management
        ("roles.read", "查看角色信息"),
        ("roles.write", "创建和编辑角色"),
        ("roles.delete", "删除角色"),
        
        # Ticket management
        ("tickets.read", "查看工单信息"),
        ("tickets.write", "创建和编辑工单"),
        ("tickets.delete", "删除工单"),
        ("tickets.assign", "分配工单"),
        
        # Warranty management
        ("warranty.read", "查看保修信息"),
        ("warranty.write", "编辑保修信息"),
        ("warranty.reindex", "重建保修索引"),
        
        # Service center management
        ("centers.read", "查看服务中心信息"),
        ("centers.write", "编辑服务中心信息"),
        
        # Audit logs
        ("audit.read", "查看审计日志"),
        
        # System administration
        ("system.admin", "系统管理权限"),
    ]
    
    permissions = {}
    for code, description in permissions_data:
        # Check if permission already exists
        existing = db.query(Permission).filter(Permission.code == code).first()
        if existing:
            permissions[code] = existing
        else:
            permission = Permission(code=code, description=description)
            db.add(permission)
            permissions[code] = permission
    
    db.commit()
    return permissions


def create_roles(db: Session, permissions: dict[str, Permission]) -> dict[str, Role]:
    """Create default roles with permissions."""
    roles_data = {
        "admin": {
            "description": "系统管理员 - 拥有全部权限",
            "permissions": list(permissions.keys())  # All permissions
        },
        "ops_manager": {
            "description": "运营经理 - 用户管理和工单查看权限",
            "permissions": [
                "users.read", "users.write",
                "tickets.read", "tickets.assign",
                "warranty.read", "warranty.reindex",
                "centers.write", "audit.read"
            ]
        },
        "agent": {
            "description": "客服专员 - 工单处理和保修查询权限",
            "permissions": [
                "tickets.read", "tickets.write",
                "warranty.read", "centers.read"
            ]
        },
        "viewer": {
            "description": "只读用户 - 仅查看权限",
            "permissions": [
                "tickets.read", "warranty.read", "centers.read"
            ]
        }
    }
    
    roles = {}
    for role_name, role_info in roles_data.items():
        # Check if role already exists
        existing = db.query(Role).filter(Role.name == role_name).first()
        if existing:
            roles[role_name] = existing
            # Update permissions if needed
            role_permissions = [permissions[code] for code in role_info["permissions"] if code in permissions]
            existing.permissions = role_permissions
        else:
            role = Role(
                name=role_name,
                description=role_info["description"]
            )
            # Assign permissions
            role_permissions = [permissions[code] for code in role_info["permissions"] if code in permissions]
            role.permissions = role_permissions
            
            db.add(role)
            roles[role_name] = role
    
    db.commit()
    return roles


def create_admin_user(db: Session, roles: dict[str, Role]) -> User:
    """Create default admin user if not exists."""
    admin_email = "admin@meidasupport.com"
    
    # Check if admin user already exists
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        # Ensure admin has admin role
        if roles["admin"] not in existing_admin.roles:
            existing_admin.roles.append(roles["admin"])
            db.commit()
        return existing_admin
    
    # Create admin user
    admin_user = User(
        email=admin_email,
        password_hash=hash_password("admin123456"),  # Default password
        display_name="系统管理员",
        is_active=True
    )
    
    # Assign admin role
    admin_user.roles = [roles["admin"]]
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    print(f"Created admin user: {admin_email}")
    print("Default password: admin123456")
    print("Please change the password after first login!")
    
    return admin_user


def seed_database():
    """Seed the database with initial data."""
    print("Starting database seeding...")
    
    db = SessionLocal()
    try:
        # Create permissions
        print("Creating permissions...")
        permissions = create_permissions(db)
        print(f"Created {len(permissions)} permissions")
        
        # Create roles
        print("Creating roles...")
        roles = create_roles(db, permissions)
        print(f"Created {len(roles)} roles")
        
        # Create admin user
        print("Creating admin user...")
        admin_user = create_admin_user(db, roles)
        print(f"Admin user: {admin_user.email}")
        
        print("Database seeding completed successfully!")
        
    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database() 