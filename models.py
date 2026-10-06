from pydantic import BaseModel, Field
from typing import Dict

class MealRating(BaseModel):
    user_id: str
    meal_id: str
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    feedback_notes: str | None = None

class RecipeSuggestion(BaseModel):
    user_id: str
    recipe_name: str
    ingredients_grams: Dict[str, float]  # e.g., {"chicken_breast": 150.0, "rice": 100.0}
    instructions: str