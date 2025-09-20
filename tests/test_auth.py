"""
Basic authentication tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.db.seed import seed_database

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Setup test database."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed database
    db = TestingSessionLocal()
    try:
        from backend.app.db.seed import create_permissions, create_roles, create_admin_user
        permissions = create_permissions(db)
        roles = create_roles(db, permissions)
        admin_user = create_admin_user(db, roles)
    finally:
        db.close()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "features" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "美大客服支持系统" in response.text


class TestAuthentication:
    """Authentication test cases."""
    
    def test_login_invalid_credentials(self, setup_database):
        """Test login with invalid credentials."""
        response = client.post("/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_valid_credentials(self, setup_database):
        """Test login with valid credentials."""
        response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "user" in data
        assert data["user"]["email"] == "admin@meidasupport.com"
        
        # Check cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
    
    def test_me_without_login(self, setup_database):
        """Test /me endpoint without login."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
    
    def test_me_with_login(self, setup_database):
        """Test /me endpoint with login."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        assert login_response.status_code == 200
        
        # Get cookies
        cookies = login_response.cookies
        
        # Test /me endpoint
        response = client.get("/api/auth/me", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@meidasupport.com"
        assert "admin" in data["roles"]
        assert len(data["permissions"]) > 0
    
    def test_logout(self, setup_database):
        """Test logout functionality."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        cookies = login_response.cookies
        
        # Logout
        response = client.post("/api/auth/logout", cookies=cookies)
        assert response.status_code == 200
        assert response.json()["ok"] is True
    
    def test_refresh_token(self, setup_database):
        """Test token refresh."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        cookies = login_response.cookies
        
        # Refresh token
        response = client.post("/api/auth/refresh", cookies=cookies)
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # Check new cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies


class TestAdmin:
    """Admin functionality test cases."""
    
    def test_get_users_without_permission(self, setup_database):
        """Test getting users without permission."""
        response = client.get("/api/admin/users")
        assert response.status_code == 401
    
    def test_get_users_with_permission(self, setup_database):
        """Test getting users with admin permission."""
        # Login as admin
        login_response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        cookies = login_response.cookies
        
        # Get users
        response = client.get("/api/admin/users", cookies=cookies)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert len(data["users"]) >= 1  # At least admin user
    
    def test_get_roles(self, setup_database):
        """Test getting roles."""
        # Login as admin
        login_response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        cookies = login_response.cookies
        
        # Get roles
        response = client.get("/api/admin/roles", cookies=cookies)
        assert response.status_code == 200
        roles = response.json()
        assert len(roles) >= 4  # admin, ops_manager, agent, viewer
        
        # Check admin role exists
        admin_role = next((r for r in roles if r["name"] == "admin"), None)
        assert admin_role is not None
        assert len(admin_role["permissions"]) > 0
    
    def test_get_permissions(self, setup_database):
        """Test getting permissions."""
        # Login as admin
        login_response = client.post("/api/auth/login", json={
            "email": "admin@meidasupport.com",
            "password": "admin123456"
        })
        cookies = login_response.cookies
        
        # Get permissions
        response = client.get("/api/admin/permissions", cookies=cookies)
        assert response.status_code == 200
        permissions = response.json()
        assert len(permissions) > 0
        
        # Check some expected permissions
        permission_codes = [p["code"] for p in permissions]
        assert "users.read" in permission_codes
        assert "users.write" in permission_codes
        assert "roles.read" in permission_codes


if __name__ == "__main__":
    pytest.main([__file__]) 