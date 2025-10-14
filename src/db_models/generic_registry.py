from src.db_models.generic_models import *
from src.db_models import generic_schemas

MODEL_REGISTRY = {
    "user_profile": {
        "model": UserProfile,
        "update_schema": UserProfileUpdate,
    },
    "user_tracking_pages":{
        "model":UserTrackingPages,
    },
    "terms_and_conditions" :{
        "model" : TermsAndCondition,
    },
    "subscription_details" : {
        "model": SubscriptionDetails,
    },
    "plan":{
        "model" : Plan,
    },
    "subscription":{
        "model" : Subscription,
    },
    "invoice":{
        "model" : Invoice,
    },
    "listings":{
        "model": Listing,
        "update_schema": ListingUpdate,
    },
    "listing_space":{
        "model": ListingSpace
    },
    "image":{
        "model": Image
    },
    
    
}  
    

    
RESPONSE_SCHEMAS_REGISTRY = {
    "user_profile": generic_schemas.UserProfileOutput,
    "app_minimum_version": generic_schemas.AppVersionResponse,
    "terms_and_conditions" :generic_schemas.TermsAndConditonOutput,
    "subscription_details" : generic_schemas.SubscriptionDetailsOutput,
    "subscription" : generic_schemas.SubscriptionOutput,
    "plan" : generic_schemas.PlanOutput,
    "listings" : generic_schemas.ListingsOutput,
    "listing_space": generic_schemas.ListingSpaceOutput,
    "image": generic_schemas.ImageOutput,

}
