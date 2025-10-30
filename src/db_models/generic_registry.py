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
    "country":{
        "model": Country
    },
    "user_visit_tracking":{
        "model": UserVisitTracking
    },
    "family_counts":{
        "model": FamilyCounts
    },
    "community_info":{
        "model": CommunityInfo
    },
    "family_number_submitted":{
        "model": FamilyNumberSubmitted
    },
    "city_state":{
        "model": CityState
    },
    "user_device_info":{
        "model": UserDeviceInfo
    },
    "post_type":{
        "model": PostType
    },
    "views_tracking":{
        "model": ViewsTracking
    },
    "favorites":{
        "model": Favorites
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
    "country": generic_schemas.CountryOutput,
    "user_visit_tracking": generic_schemas.UserVisitTrackingOutput,
    "family_counts": generic_schemas.FamilyCountsOutput,
    "community_info": generic_schemas.CommunityInfoOutput,
    "family_number_submitted": generic_schemas.FamilyNumberSubmittedOutput,
    "city_state": generic_schemas.CityStateOutput,
    "user_device_info": generic_schemas.UserDeviceInfoOutput,
    "post_type": generic_schemas.PostTypeOutput,
    "favorites": generic_schemas.FavoritesOutput,
}
