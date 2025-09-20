"""
Role-Based Access Control (RBAC) service for managing user permissions.
"""
from typing import List, Optional, Set, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status
from ..models.user import User
from ..models.role import Role, Permission, RoleCreate, RoleUpdate, RoleResponse, PermissionResponse


# Permission codes organized by category
PERMISSIONS = {
    "users": [
        "users.read",
        "users.write",
    ],
    "roles": [
        "roles.read",
        "roles.write",
    ],
    "permissions": [
        "permissions.read",
    ],
    "audit": [
        "audit.read",
    ],
    "tickets": [
        "tickets.read",
        "tickets.write", 
        "tickets.assign",
        "tickets.complete",
        "tickets.upload",
    ],
    "warranty": [
        "warranty.read",
        "warranty.reindex",
    ],
    "centers": [
        "centers.write",
    ],
    "ai": [
        "ai.workflow.run",
        "ai.chat",
    ],
    "geo": [
        "geo.read",
    ],
    "system": [
        "system.admin",
    ]
}

# Flatten all permissions into a single list
ALL_PERMISSIONS = []
for category, perms in PERMISSIONS.items():
    ALL_PERMISSIONS.extend(perms)

# System roles and their core permissions that cannot be removed
SYSTEM_ROLE_CORE_PERMISSIONS = {
    "admin": ALL_PERMISSIONS,  # Admin has all permissions
    "agent": ["tickets.read", "tickets.write", "tickets.upload", "warranty.read"],
    "viewer": ["tickets.read", "warranty.read"],
    "ops_manager": ["users.read", "tickets.read", "tickets.assign", "tickets.complete", "warranty.reindex", "centers.write"]
}


class RBACService:
    """Service for managing roles and permissions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def aggregate_permissions(self, user: User) -> Set[str]:
        """
        Aggregate all permissions for a user from their roles.
        
        Args:
            user: User to aggregate permissions for
        
        Returns:
            Set of permission codes
        """
        permissions = set()
        
        # Load user with roles and permissions
        user_with_roles = self.db.query(User).options(
            joinedload(User.roles).joinedload(Role.permissions)
        ).filter(User.id == user.id).first()
        
        if not user_with_roles:
            return permissions
        
        # Aggregate permissions from all roles
        for role in user_with_roles.roles:
            for permission in role.permissions:
                permissions.add(permission.code)
        
        return permissions
    
    def get_permissions_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all permissions organized by category.
        
        Returns:
            Dictionary with category as key and list of permissions as value
        """
        permissions = self.db.query(Permission).all()
        result = {}
        
        for permission in permissions:
            category = permission.category
            if category not in result:
                result[category] = []
            
            result[category].append({
                "id": permission.id,
                "code": permission.code,
                "description": permission.description,
                "category": permission.category
            })
        
        return result
    
    def validate_permission_codes(self, codes: List[str]) -> bool:
        """
        Validate that all permission codes exist.
        
        Args:
            codes: List of permission codes to validate
        
        Returns:
            True if all codes are valid, False otherwise
        """
        if not codes:
            return True
        
        existing_codes = {p.code for p in self.db.query(Permission.code).all()}
        return all(code in existing_codes for code in codes)
    
    def user_has_permission(self, user: User, permission_code: str) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user: User to check
            permission_code: Permission code to check (e.g., "users.read")
        
        Returns:
            True if user has the permission, False otherwise
        """
        # Admin role bypasses all permission checks
        if self.user_has_role(user, "admin"):
            return True
        
        # Check if user has the permission through any of their roles
        for role in user.roles:
            for permission in role.permissions:
                if permission.code == permission_code:
                    return True
        
        return False
    
    def user_has_permissions(self, user: User, permission_codes: List[str]) -> bool:
        """
        Check if a user has all specified permissions.
        
        Args:
            user: User to check
            permission_codes: List of permission codes to check
        
        Returns:
            True if user has all permissions, False otherwise
        """
        # Admin role bypasses all permission checks
        if self.user_has_role(user, "admin"):
            return True
        
        # Get all user's permissions
        user_permissions = self.get_user_permissions(user)
        
        # Check if all required permissions are present
        for permission_code in permission_codes:
            if permission_code not in user_permissions:
                return False
        
        return True
    
    def user_has_role(self, user: User, role_name: str) -> bool:
        """
        Check if a user has a specific role.
        
        Args:
            user: User to check
            role_name: Role name to check
        
        Returns:
            True if user has the role, False otherwise
        """
        for role in user.roles:
            if role.name == role_name:
                return True
        return False
    
    def get_user_permissions(self, user: User) -> Set[str]:
        """
        Get all permissions for a user across all their roles.
        
        Args:
            user: User to get permissions for
        
        Returns:
            Set of permission codes
        """
        permissions = set()
        for role in user.roles:
            for permission in role.permissions:
                permissions.add(permission.code)
        return permissions
    
    def get_user_roles(self, user: User) -> List[str]:
        """
        Get all role names for a user.
        
        Args:
            user: User to get roles for
        
        Returns:
            List of role names
        """
        return [role.name for role in user.roles]
    
    def assign_role_to_user(self, user: User, role_name: str) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user: User to assign role to
            role_name: Name of role to assign
        
        Returns:
            True if role was assigned, False if role doesn't exist
        """
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False
        
        if role not in user.roles:
            user.roles.append(role)
            self.db.commit()
        
        return True
    
    def remove_role_from_user(self, user: User, role_name: str) -> bool:
        """
        Remove a role from a user.
        
        Args:
            user: User to remove role from
            role_name: Name of role to remove
        
        Returns:
            True if role was removed, False if user didn't have the role
        """
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False
        
        if role in user.roles:
            user.roles.remove(role)
            self.db.commit()
            return True
        
        return False
    
    def assign_roles_to_user(self, user: User, role_names: List[str]) -> List[str]:
        """
        Assign multiple roles to a user, replacing existing roles.
        
        Args:
            user: User to assign roles to
            role_names: List of role names to assign
        
        Returns:
            List of role names that were successfully assigned
        """
        # Get roles from database
        roles = self.db.query(Role).filter(Role.name.in_(role_names)).all()
        
        # Replace user's roles
        user.roles = roles
        self.db.commit()
        
        return [role.name for role in roles]
    
    def create_role(self, role_data: RoleCreate) -> Role:
        """
        Create a new role with permissions.
        
        Args:
            role_data: Role creation data
        
        Returns:
            Created role
        """
        # Create role
        role = Role(
            name=role_data.name,
            description=role_data.description
        )
        
        # Assign permissions
        if role_data.permission_codes:
            permissions = self.db.query(Permission).filter(
                Permission.code.in_(role_data.permission_codes)
            ).all()
            role.permissions = permissions
        
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        
        return role
    
    def update_role(self, role_id: int, role_data: RoleUpdate) -> Optional[Role]:
        """
        Update a role with system role protection.
        
        Args:
            role_id: ID of role to update
            role_data: Role update data
        
        Returns:
            Updated role or None if not found
            
        Raises:
            HTTPException: If trying to modify system role inappropriately
        """
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return None
        
        # System role protection
        if role.is_system:
            # System roles cannot be renamed
            if role_data.name is not None and role_data.name != role.name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"System role '{role.name}' cannot be renamed"
                )
            
            # Validate that core permissions are not removed from system roles
            if role_data.permission_codes is not None and role.name in SYSTEM_ROLE_CORE_PERMISSIONS:
                core_permissions = set(SYSTEM_ROLE_CORE_PERMISSIONS[role.name])
                new_permissions = set(role_data.permission_codes)
                
                if not core_permissions.issubset(new_permissions):
                    missing_perms = core_permissions - new_permissions
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"System role '{role.name}' must retain core permissions: {list(missing_perms)}"
                    )
        
        # Validate permission codes exist
        if role_data.permission_codes is not None:
            if not self.validate_permission_codes(role_data.permission_codes):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more permission codes are invalid"
                )
        
        # Update basic fields
        if role_data.name is not None:
            role.name = role_data.name
        if role_data.description is not None:
            role.description = role_data.description
        
        # Update permissions if provided
        if role_data.permission_codes is not None:
            permissions = self.db.query(Permission).filter(
                Permission.code.in_(role_data.permission_codes)
            ).all()
            role.permissions = permissions
        
        self.db.commit()
        self.db.refresh(role)
        
        return role
    
    def delete_role(self, role_id: int) -> bool:
        """
        Delete a role with system role and user reference protection.
        
        Args:
            role_id: ID of role to delete
        
        Returns:
            True if role was deleted, False if not found
            
        Raises:
            HTTPException: If trying to delete system role or role with users
        """
        role = self.db.query(Role).options(joinedload(Role.users)).filter(Role.id == role_id).first()
        if not role:
            return False
        
        # System roles cannot be deleted
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"System role '{role.name}' cannot be deleted"
            )
        
        # Cannot delete role if it has users assigned
        if role.users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{role.name}' cannot be deleted because it is assigned to {len(role.users)} user(s). Please remove the role from all users first."
            )
        
        self.db.delete(role)
        self.db.commit()
        
        return True
    
    def get_role(self, role_id: int) -> Optional[RoleResponse]:
        """
        Get a role by ID with permissions and user count.
        
        Args:
            role_id: ID of role to get
        
        Returns:
            Role response or None if not found
        """
        role = self.db.query(Role).options(
            joinedload(Role.permissions),
            joinedload(Role.users)
        ).filter(Role.id == role_id).first()
        
        if not role:
            return None
        
        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=[
                PermissionResponse(
                    id=perm.id,
                    code=perm.code,
                    description=perm.description,
                    category=perm.category,
                    created_at=perm.created_at,
                    updated_at=perm.updated_at
                ) for perm in role.permissions
            ],
            permissions_count=len(role.permissions),
            user_count=len(role.users)
        )
    
    def get_all_roles(self) -> List[RoleResponse]:
        """
        Get all roles with permissions and user counts.
        
        Returns:
            List of role responses
        """
        roles = self.db.query(Role).options(
            joinedload(Role.permissions),
            joinedload(Role.users)
        ).all()
        
        return [
            RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system=role.is_system,
                created_at=role.created_at,
                updated_at=role.updated_at,
                permissions=[
                    PermissionResponse(
                        id=perm.id,
                        code=perm.code,
                        description=perm.description,
                        category=perm.category,
                        created_at=perm.created_at,
                        updated_at=perm.updated_at
                    ) for perm in role.permissions
                ],
                permissions_count=len(role.permissions),
                user_count=len(role.users)
            ) for role in roles
        ]
    
    def get_all_permissions(self) -> List[PermissionResponse]:
        """
        Get all available permissions.
        
        Returns:
            List of permission responses
        """
        permissions = self.db.query(Permission).all()
        
        return [
            PermissionResponse(
                id=perm.id,
                code=perm.code,
                description=perm.description,
                category=perm.category,
                created_at=perm.created_at,
                updated_at=perm.updated_at
            ) for perm in permissions
        ]
    
    def assign_roles_to_user(self, user_id: int, role_ids: List[int]) -> bool:
        """
        Assign roles to a user (replaces existing roles).
        
        Args:
            user_id: ID of user to assign roles to
            role_ids: List of role IDs to assign
        
        Returns:
            True if successful, False if user not found
            
        Raises:
            HTTPException: If any role ID is invalid
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Validate role IDs exist
        if role_ids:
            existing_role_ids = {r.id for r in self.db.query(Role.id).filter(Role.id.in_(role_ids)).all()}
            invalid_ids = set(role_ids) - existing_role_ids
            if invalid_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role IDs: {list(invalid_ids)}"
                )
        
        # Get roles and assign to user
        roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []
        user.roles = roles
        
        self.db.commit()
        return True
    
    def get_roles_paginated(self, query: str = None, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Get roles with pagination and optional search.
        
        Args:
            query: Optional search query for role name
            page: Page number (1-based)
            page_size: Number of items per page
        
        Returns:
            Dictionary with items, page info, and total count
        """
        # Base query
        base_query = self.db.query(Role).options(
            joinedload(Role.permissions),
            joinedload(Role.users)
        )
        
        # Apply search filter
        if query:
            base_query = base_query.filter(Role.name.ilike(f"%{query}%"))
        
        # Get total count
        total = base_query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        roles = base_query.offset(offset).limit(page_size).all()
        
        # Convert to response format
        items = [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_system": role.is_system,
                "permissions_count": len(role.permissions),
                "user_count": len(role.users),
                "created_at": role.created_at,
                "updated_at": role.updated_at
            } for role in roles
        ]
        
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        } 