from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth.auth import get_current_admin_user
from ..dependencies import get_category_service
from ..models.user import User
from ..schemas.category import Category, CategoryCreate, CategoryUpdate
from ..services.category_service import CategoryService
from ..services.exceptions import CategoryAlreadyExistsError, CategoryNotFoundError

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[Category])
def list_categories(
    include_inactive: bool = Query(False, description="Возвращать ли неактивные категории"),
    category_service: CategoryService = Depends(get_category_service),
) -> List[Category]:
    return category_service.list_categories(include_inactive=include_inactive)


@router.post("/", response_model=Category)
def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_admin_user),
    category_service: CategoryService = Depends(get_category_service),
) -> Category:
    try:
        return category_service.create_category(category_in)
    except CategoryAlreadyExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: User = Depends(get_current_admin_user),
    category_service: CategoryService = Depends(get_category_service),
) -> Category:
    try:
        return category_service.update_category(category_id, category_update)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Category not found") from exc
    except CategoryAlreadyExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_admin_user),
    category_service: CategoryService = Depends(get_category_service),
) -> dict[str, str]:
    try:
        category_service.delete_category(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Category not found") from exc
    return {"message": "Category deleted successfully"}
