"""
RBAC v2 基础功能测试
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.role import Role, Permission
from backend.app.core.security import hash_password
from backend.app.services.rbac_service import PERMISSIONS, SYSTEM_ROLE_CORE_PERMISSIONS

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def client():
    """Create test client with fresh database"""
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as test_client:
        yield test_client
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_permissions(db_session):
    """Create sample permissions"""
    permissions = []
    for category, codes in PERMISSIONS.items():
        for code in codes[:2]:  # Only create first 2 permissions per category for testing
            perm = Permission(
                code=code,
                description=f"Test permission: {code}",
                category=category
            )
            db_session.add(perm)
            permissions.append(perm)
    
    db_session.commit()
    return permissions

@pytest.fixture
def sample_roles(db_session, sample_permissions):
    """Create sample roles"""
    # Create admin role with all permissions
    admin_role = Role(
        name="admin",
        description="Administrator role",
        is_system=True
    )
    admin_role.permissions = sample_permissions
    db_session.add(admin_role)
    
    # Create viewer role with limited permissions
    viewer_role = Role(
        name="viewer",
        description="Viewer role",
        is_system=False
    )
    viewer_permissions = [p for p in sample_permissions if p.code.endswith('.read')]
    viewer_role.permissions = viewer_permissions
    db_session.add(viewer_role)
    
    db_session.commit()
    return [admin_role, viewer_role]

@pytest.fixture
def admin_user(db_session, sample_roles):
    """Create admin user"""
    admin_role = next(role for role in sample_roles if role.name == "admin")
    
    user = User(
        email="admin@test.com",
        password_hash=hash_password("testpass123"),
        display_name="Test Admin",
        is_active=True
    )
    user.roles = [admin_role]
    db_session.add(user)
    db_session.commit()
    
    return user

@pytest.fixture
def viewer_user(db_session, sample_roles):
    """Create viewer user"""
    viewer_role = next(role for role in sample_roles if role.name == "viewer")
    
    user = User(
        email="viewer@test.com", 
        password_hash=hash_password("testpass123"),
        display_name="Test Viewer",
        is_active=True
    )
    user.roles = [viewer_role]
    db_session.add(user)
    db_session.commit()
    
    return user

def login_user(client, email, password):
    """Helper function to login user and get cookies"""
    response = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    return response.cookies

class TestPermissionsAPI:
    """Test permissions API endpoints"""
    
    def test_get_permissions_unauthorized(self, client):
        """Test getting permissions without authentication"""
        response = client.get("/api/admin/permissions")
        assert response.status_code == 401
    
    def test_get_permissions_authorized(self, client, admin_user, sample_permissions):
        """Test getting permissions with proper authorization"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        response = client.get("/api/admin/permissions", cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check structure
        for category in data:
            assert "category" in category
            assert "items" in category
            assert isinstance(category["items"], list)

class TestRolesAPI:
    """Test roles API endpoints"""
    
    def test_get_roles_unauthorized(self, client):
        """Test getting roles without authentication"""
        response = client.get("/api/admin/roles")
        assert response.status_code == 401
    
    def test_get_roles_authorized(self, client, admin_user, sample_roles):
        """Test getting roles with proper authorization"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        response = client.get("/api/admin/roles", cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        
        assert len(data["items"]) == 2  # admin and viewer roles
        
        # Check admin role
        admin_role = next(role for role in data["items"] if role["name"] == "admin")
        assert admin_role["is_system"] == True
        assert admin_role["permissions_count"] > 0
    
    def test_create_role(self, client, admin_user, sample_permissions):
        """Test creating a new role"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        role_data = {
            "name": "test_role",
            "description": "Test role for testing",
            "permission_codes": ["users.read", "tickets.read"]
        }
        
        response = client.post("/api/admin/roles", json=role_data, cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "test_role"
        assert data["description"] == "Test role for testing"
        assert data["is_system"] == False
    
    def test_create_role_duplicate_name(self, client, admin_user, sample_roles):
        """Test creating role with duplicate name"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        role_data = {
            "name": "admin",  # Duplicate name
            "description": "Duplicate admin role",
            "permission_codes": ["users.read"]
        }
        
        response = client.post("/api/admin/roles", json=role_data, cookies=cookies)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_update_role(self, client, admin_user, sample_roles):
        """Test updating a role"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        # Get viewer role ID
        roles_response = client.get("/api/admin/roles", cookies=cookies)
        viewer_role = next(role for role in roles_response.json()["items"] if role["name"] == "viewer")
        
        update_data = {
            "description": "Updated viewer role description",
            "permission_codes": ["users.read", "audit.read"]
        }
        
        response = client.patch(f"/api/admin/roles/{viewer_role['id']}", json=update_data, cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert data["description"] == "Updated viewer role description"
    
    def test_update_system_role_name_forbidden(self, client, admin_user, sample_roles):
        """Test that system role names cannot be changed"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        # Get admin role ID
        roles_response = client.get("/api/admin/roles", cookies=cookies)
        admin_role = next(role for role in roles_response.json()["items"] if role["name"] == "admin")
        
        update_data = {
            "name": "super_admin"  # Try to change system role name
        }
        
        response = client.patch(f"/api/admin/roles/{admin_role['id']}", json=update_data, cookies=cookies)
        assert response.status_code == 400
        assert "cannot be renamed" in response.json()["detail"]
    
    def test_delete_role(self, client, admin_user, sample_roles):
        """Test deleting a role"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        # Create a test role to delete
        role_data = {
            "name": "deletable_role",
            "description": "Role that can be deleted",
            "permission_codes": ["users.read"]
        }
        
        create_response = client.post("/api/admin/roles", json=role_data, cookies=cookies)
        role_id = create_response.json()["id"]
        
        # Delete the role
        response = client.delete(f"/api/admin/roles/{role_id}", cookies=cookies)
        assert response.status_code == 200
        assert response.json()["ok"] == True
    
    def test_delete_system_role_forbidden(self, client, admin_user, sample_roles):
        """Test that system roles cannot be deleted"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        # Get admin role ID
        roles_response = client.get("/api/admin/roles", cookies=cookies)
        admin_role = next(role for role in roles_response.json()["items"] if role["name"] == "admin")
        
        response = client.delete(f"/api/admin/roles/{admin_role['id']}", cookies=cookies)
        assert response.status_code == 400
        assert "cannot be deleted" in response.json()["detail"]

class TestUserRoleAssignment:
    """Test user role assignment"""
    
    def test_assign_roles_to_user(self, client, admin_user, viewer_user, sample_roles):
        """Test assigning roles to user"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        # Get role IDs
        roles_response = client.get("/api/admin/roles", cookies=cookies)
        role_ids = [role["id"] for role in roles_response.json()["items"]]
        
        assignment_data = {
            "role_ids": role_ids
        }
        
        response = client.post(f"/api/admin/users/{viewer_user.id}/roles", 
                              json=assignment_data, cookies=cookies)
        assert response.status_code == 200
        assert response.json()["ok"] == True

class TestAuthMeExtension:
    """Test /api/auth/me extension with effective permissions"""
    
    def test_me_endpoint_includes_effective_permissions(self, client, admin_user):
        """Test that /me endpoint returns effective_permissions"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        response = client.get("/api/auth/me", cookies=cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert "effective_permissions" in data
        assert isinstance(data["effective_permissions"], list)
        assert len(data["effective_permissions"]) > 0
        
        # Admin should have many permissions
        assert "users.read" in data["effective_permissions"]
        assert "users.write" in data["effective_permissions"]

class TestPermissionDependencies:
    """Test permission-based dependencies"""
    
    def test_access_with_sufficient_permissions(self, client, admin_user):
        """Test accessing endpoint with sufficient permissions"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        response = client.get("/api/admin/roles", cookies=cookies)
        assert response.status_code == 200
    
    def test_access_with_insufficient_permissions(self, client, viewer_user):
        """Test accessing endpoint with insufficient permissions"""
        cookies = login_user(client, "viewer@test.com", "testpass123")
        
        # Viewer should not be able to create roles
        role_data = {
            "name": "unauthorized_role",
            "description": "Should not be created",
            "permission_codes": ["users.read"]
        }
        
        response = client.post("/api/admin/roles", json=role_data, cookies=cookies)
        assert response.status_code == 403

class TestRBACIntegration:
    """Integration tests for RBAC system"""
    
    def test_complete_role_lifecycle(self, client, admin_user, sample_permissions):
        """Test complete role lifecycle: create -> update -> assign -> delete"""
        cookies = login_user(client, "admin@test.com", "testpass123")
        
        # 1. Create role
        role_data = {
            "name": "lifecycle_test_role",
            "description": "Role for lifecycle testing",
            "permission_codes": ["users.read", "tickets.read"]
        }
        
        create_response = client.post("/api/admin/roles", json=role_data, cookies=cookies)
        assert create_response.status_code == 200
        role_id = create_response.json()["id"]
        
        # 2. Update role
        update_data = {
            "description": "Updated description",
            "permission_codes": ["users.read", "tickets.read", "audit.read"]
        }
        
        update_response = client.patch(f"/api/admin/roles/{role_id}", json=update_data, cookies=cookies)
        assert update_response.status_code == 200
        
        # 3. Get role to verify update
        get_response = client.get(f"/api/admin/roles/{role_id}", cookies=cookies)
        assert get_response.status_code == 200
        role_data = get_response.json()
        assert "audit.read" in role_data["permissions"]
        
        # 4. Delete role
        delete_response = client.delete(f"/api/admin/roles/{role_id}", cookies=cookies)
        assert delete_response.status_code == 200
        
        # 5. Verify role is deleted
        get_deleted_response = client.get(f"/api/admin/roles/{role_id}", cookies=cookies)
        assert get_deleted_response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 