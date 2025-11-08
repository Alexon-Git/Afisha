from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    slug: str
    is_active: bool = True


class CategoryCreate(BaseModel):
    name: str
    slug: str | None = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None


class Category(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
