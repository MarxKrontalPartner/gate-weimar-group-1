from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str | None = Field(None, max_length=255, description="Full name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "securepassword123",
                "full_name": "John Doe",
            }
        }


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }


class UserResponse(BaseModel):
    """Schema for user data in responses."""
    user_id: int
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
            }
        }


class TokenResponse(BaseModel):
    """Schema for token response after login."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "user_id": 1,
                    "email": "user@example.com",
                    "username": "johndoe",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_superuser": False,
                },
            }
        }