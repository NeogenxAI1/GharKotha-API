import os
import tempfile
from typing import Any, List, Literal, Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from auth.utils import get_user_id_from_token
from core.database import SessionLocal
from src.db_models.generic_registry import MODEL_REGISTRY, RESPONSE_SCHEMAS_REGISTRY
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from sqlalchemy import text, func
import stripe
from pathlib import Path
from utils.emailer import build_invoice_html, send_invoice_email
from utils.pdftry import generate_invoice_pdf
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from src.db_models.generic_models import UserVisitTracking, UserDeviceInfoCreate,CommunityInfoCreate,FamilyNumberSubmittedCreate,UserTrackingUpdate,UserTrackingCreate, FamilyCounts, CommunityInfo, PostType, FamilyNumberSubmitted, CityState, UserDeviceInfo
from functools import lru_cache

router = APIRouter(prefix="/generic")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from src.db_models.generic_models import AppMinimumVersion, Invoice, Listing, ListingSpace, Subscription, Image
from src.db_models.generic_schemas import AppVersionResponse, CityStateOutput, ListingOut,PostTypeOutput, CommunityInfoOutput, UserDeviceInfoOutput

@router.get("/app_version", response_model=AppVersionResponse)
def get_app_version(db: Session = Depends(get_db)):
    schema = RESPONSE_SCHEMAS_REGISTRY.get("app_version")
    latest_version = (
        db.query(AppMinimumVersion)
        .order_by(AppMinimumVersion.created_at.desc())
        .first()
    )

    if not latest_version:
        raise HTTPException(status_code=404, detail="Version info not found.")
    
    serialized = schema.from_orm(latest_version)
    return JSONResponse(content=jsonable_encoder(serialized))

def get_current_active_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    # if get_subscription_status(user_id,db)=='expired':
    #     raise HTTPException(status_code=405, detail="Expired")
    return user_id

def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[str]:
    """
    Same as get_current_active_user but does not raise 401.
    Returns user_id if token is valid, else None.
    """
    if not authorization:
        return None  # public request
    
    try:
        token = authorization.replace("Bearer ", "")
        user_id = get_user_id_from_token(token)
        return user_id
    except Exception:
        # invalid token or decoding error
        return None
    
def subscriptionType(db, user_id):
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    return subscription.status if subscription and subscription.status else "trial"

# GET user?name=Alice&email=alice@example.com
# def get_subscription_status(user_id,db):
#     Subscriptions = db.query(Subscription.status).filter(Subscription.user_id == user_id).first()
#     return Subscriptions.status if Subscriptions else None


@router.get("/{model_name}")
def read_item(
    model_name: str,
    request: Request,
    mode: Optional[str] = Query(None),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    model_entry = MODEL_REGISTRY.get(model_name.lower())
    if not model_entry:
        raise HTTPException(status_code=404, detail="Model not found")

    schema = RESPONSE_SCHEMAS_REGISTRY.get(model_name.lower())
    if not schema:
        raise HTTPException(
            status_code=500, detail="No response schema defined for this model")

    model = model_entry["model"]
    # Get all query parameters from the request
    filters = dict(request.query_params)
    filters.pop("mode", None)

    if hasattr(model, "user_id") and current_user:
        filters["user_id"] = current_user

    # Validate filters against model columns
    mapper = inspect(model)
    valid_column_names = {col.key for col in mapper.attrs}
    invalid_keys = set(filters) - valid_column_names
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filter(s): {', '.join(invalid_keys)}"
        )
    
    # Build query with dynamic filters
    subscription = subscriptionType(db, current_user)
    if subscription != "active" and model_name.lower() in ["language_scenario", "language_scenario_topics"]:
        results = db.query(model).filter_by(**filters).limit(5)
    else:
        results = db.query(model).filter_by(**filters).all()
    # results = db.query(model).filter_by(**filters).all()
    serialized = [schema.from_orm(obj) for obj in results]
    return JSONResponse(content=jsonable_encoder(serialized))

# UPDATE


@router.put("/{model_name}/{item_id}")
def update_item(
    model_name: str,
    item_id: int,
    item_data: dict[str, Any] = Body(...),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    print(f"oh yes - i m here ------------------------ with item id: {item_id} and model_name : ", model_name)
    model_entry = MODEL_REGISTRY.get(model_name)
    if not model_entry:
        raise HTTPException(status_code=404, detail="Model not found")

    model = model_entry["model"]
    UpdateSchema = model_entry["update_schema"]
    if not model_entry:
        raise HTTPException(status_code=404, detail="Model not found")

    # db_item = db.get(model, current_user) ##PK
    db_item = db.get(model, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = UpdateSchema(**item_data).dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item

# DELETE


@router.delete("/{model_name}")
def delete_item(
    model_name: str,
    request: Request,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    model_entry = MODEL_REGISTRY.get(model_name)
    if not model_entry:
        raise HTTPException(status_code=404, detail="Model not found")

    item_data = {}
    model = model_entry["model"]
    query_params = dict(request.query_params)
    filters = {}

    if hasattr(model, "user_id") and current_user:
        filters["user_id"] = current_user

    for key, value in query_params.items():
        if hasattr(model, key):
            filters[key] = value

    if not filters:
        raise HTTPException(
            status_code=400, detail="At least one valid filter parameter is required.")

    query = db.query(model).filter_by(**filters)
    items = query.all()

    if not items:
        raise HTTPException(
            status_code=404, detail="No items found matching the filters.")

    deleted_count = 0
    for item in items:
        db.delete(item)
        deleted_count += 1

    db.commit()

    return {"detail": f"Deleted {deleted_count} item(s) from {model_name}."}


# insert into table


@router.post("/{model_name}")
def create_item(
    model_name: str,
    item_data: dict[str, Any] = Body(...),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    model_entry = MODEL_REGISTRY.get(model_name)
    if not model_entry:
        raise HTTPException(status_code=404, detail="Model not found")

    # CreateSchema = model_entry["create_schema"]
    model = model_entry["model"]
    if hasattr(model, "user_id") and current_user:
        item_data["user_id"] = current_user

    try:
        db_item = model(**item_data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item
    except IntegrityError as e:
        db.rollback()
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(
                status_code=400, detail="Row already exist for this user")
        raise HTTPException(
            status_code=400, detail="Integrity error: " + str(e.orig))

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Error creating item: {str(e)}")

from src.db_models.generic_models import UserProfile
@router.get("/user_profile/exists")
def check_user_profile_exists(
    # user_id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    user_id= current_user
    exists = db.query(UserProfile).filter(UserProfile.user_id == user_id).first() is not None
    return JSONResponse(content={"isValid": exists})

from pathlib import Path as SysPath
custom_router = APIRouter(prefix="/custom")

# Mukesh Payment route
# Secrete key
# class PaymentIntentRequest(BaseModel):
#     amount: int   
#     currency: str
#     plan_name: str
#     # user_id : str
# stripe.api_key = os.getenv("STRIPE_API_KEY") 
# WEBHOOK_SECRET = "whsec_Hrk6iWEnpB8K8pihIapTjHYedBoZ3FAw" # Global sandbox key
# # WEBHOOK_SECRET = "whsec_65de4521913b6fa18691fa43eee81078c9cb94367477bd449ecd779ce4ea81a0"
# #Local key
# @custom_router.post("/create-payment-intent")
# def create_payment_intent(data: PaymentIntentRequest,
#                           current_user=Depends(get_current_active_user),
#     db: Session = Depends(get_db)
#     ):
#     try:
#         #Creating invoice in database
#         new_invoice = Invoice(
#             user_id=current_user,   
#             # subscription_id=data.subscription_id,  
#             plan_name = data.plan_name,
#             amount=data.amount / 100.0,     # store as dollars instead of cents
#             paid=False
#         )
#         db.add(new_invoice)
#         db.commit()
#         db.refresh(new_invoice)
        
#         # Create payment intent with Stripe
#         intent = stripe.PaymentIntent.create(
#             amount=data.amount,
#             currency=data.currency,
#             automatic_payment_methods={"enabled": True},
#             metadata = {
#                 "user_id":current_user,
#                 "plan_name": data.plan_name,
#                 "invoice_id": str(new_invoice.id)
#             }
#         )
#         # print(f"Inside create payment intent with invoice id:{new_invoice.id}")
#         return {"client_secret": intent.client_secret, "invoice_id": new_invoice.id}
#     except Exception as e:
#         print(f"Error details for payment0intent {str(e)}")
#         raise HTTPException(status_code=400, detail=str(e))



# def format_amount_for_email(amount_minor: int, currency: str) -> str:
#     c = currency.upper()
#     if c in ZERO_DECIMAL:
#         return f"{c} {amount_minor:,.0f}"
#     return f"{c} {amount_minor/100:,.2f}"
# ZERO_DECIMAL = {"BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF","UGX","VND","VUV","XAF","XOF","XPF"}
# @custom_router.post("/webhook")
# async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
#     raw_payload: bytes = await request.body()
#     sig_header = request.headers.get("stripe-signature")

#     try:
#         event = stripe.Webhook.construct_event(
#             payload=raw_payload.decode("utf-8"),
#             sig_header=sig_header,
#             secret=WEBHOOK_SECRET,
#         )
#     except stripe.error.SignatureVerificationError:
#         raise HTTPException(status_code=400, detail="Invalid signature")
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid payload")

#     # --- Handle events ---
#     if event["type"] == "payment_intent.succeeded":
#         intent = event["data"]["object"]  
#         # Common fields
#         pi_id = intent["id"]
#         currency = (intent.get("currency") or "usd").upper()
#         is_zero_decimal = currency in ZERO_DECIMAL

#         # Prefer amount_received; fall back to amount
#         amount_minor = intent.get("amount_received") or intent.get("amount") or 0
#         amount_major = amount_minor if is_zero_decimal else amount_minor / 100.0

#         # Metadata (optional but super useful)
#         md = intent.get("metadata", {}) or {}
#         user_id = md.get("user_id")
#         invoice_id = md.get("invoice_id")
#         plan_name = md.get("plan_name") or intent.get("description") or "Subscription"
#         quantity = None
#         try:
#             if md.get("quantity"):
#                 quantity = float(md["quantity"])
#         except Exception:
#             quantity = None
#         unit = md.get("unit")  # e.g., "months", "seats"

#         # print(f"payment succeeded for user {user_id}, invoice {invoice_id}, amount {amount_major} {currency}")

#         # --- Mark invoice paid in your DB ---
#         if invoice_id:
#             inv = db.query(Invoice).filter(Invoice.id == int(invoice_id)).first()
#             if inv:
#                 inv.paid = True
#                 db.commit()

#         # --- Extend subscription by 30 days ---
#         if user_id:
#             sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
#             if sub:
#                 now_utc = datetime.now(timezone.utc)

#                 end = sub.end_date
#                 if end is not None:
#                     if end.tzinfo is None:
#                         end = end.replace(tzinfo=timezone.utc)

#                 if end and end > now_utc:
#                     sub.end_date = end + timedelta(days=30)
#                 else:
#                     sub.end_date = now_utc + timedelta(days=30)

#                 sub.status = "active"
#                 sub.plan_id = 1
#                 db.commit()
#                 print(f"📌 Subscription for user {user_id} extended until {sub.end_date}")

#         customer_name = ""
#         customer_email = ""

#         try:
#             user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
#             if user:
#                 customer_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
#                 customer_email = (user.email or "").strip()
#         except Exception as e:
#             print(f"error in name details {e}")
#             pass
        
#         print(f"Customer name: {customer_name}")
#         # Fallback to charge billing_details if needed
#         charge = None
#         try:
#             charges = intent.get("charges", {}).get("data", [])
#             if charges:
#                 charge = charges[0]
#                 if not customer_email:
#                     customer_email = (charge.get("billing_details", {}).get("email") or "").strip()
#                 if not customer_name:
#                     customer_name = (charge.get("billing_details", {}).get("name") or "").strip()
#         except Exception:
#             pass

#         # Stripe receipt URL (handy to include in invoice PDF as a “paid via Stripe” link)
#         receipt_url = ""
#         if charge:
#             receipt_url = (charge.get("receipt_url") or "").strip()

#         # --- Company / biller info - can be fetched from database if needed
#         company_name = "Neogenxai Pvt. Ltd."
#         company_location = "Bhaktapur, Nepal"
#         company_email = "itadmin@neogenxai.com"
#         phone_number = "+977 9762656555"


#         issue_dt_local = datetime.now(ZoneInfo("Asia/Kathmandu")).replace(tzinfo=None)  # your generator expects naive
#         # out_path = os.path.join("invoices", f"invoice_{pi_id}.pdf")
#         os.makedirs("invoices", exist_ok=True)


#         pdf_bytes = generate_invoice_pdf(
#             customer_name=customer_name or "Customer",
#             customer_email=customer_email or "unknown@example.com",
#             amount=float(amount_major),
#             plan_name=plan_name,
#             quantity=quantity,                 
#             unit=unit,                         
#             company_name=company_name,
#             company_location=company_location,
#             company_email=company_email,
#             phone_number=phone_number,
#             currency=currency,
#             invoice_number=md.get("invoice_number") or f"INV-{pi_id[:8].upper()}",
#             issue_date=issue_dt_local,
#             due_days=0,                        
#             stripe_payment_url=receipt_url,    # links to Stripe’s receipt
#             # output_path=out_path,
#         )
#         # print(f"🧾 Invoice PDF saved to {pdf_path}")
        
#         amount_display = format_amount_for_email(amount_minor, currency)

#         html_body = build_invoice_html(
#             customer_name=customer_name or "Customer",
#             customer_email=customer_email or "unknown@example.com",
#             plan_name=plan_name,
#             currency=currency,
#             amount=float(amount_major),                
#             quantity=quantity,                         
#             unit=unit,                                
#             invoice_number=md.get("invoice_number") or f"INV-{pi_id[:8].upper()}",
#             issue_date_yyyy_mm_dd=issue_dt_local.strftime("%Y-%m-%d"),
#             due_date_yyyy_mm_dd=issue_dt_local.strftime("%Y-%m-%d"), 
#             receipt_url=receipt_url or None,
#             company_name="Neogenxai Pvt. Ltd.",
#             company_location="Bhaktapur, Nepal",
#             company_email="itadmin@neogenxai.com",
#             phone_number="+977 9762656555",
#         )

#         if customer_email:
#             try:
#                 send_invoice_email(
#                     to_email=customer_email,
#                     subject=f"Your Invoice {md.get('invoice_number') or f'INV-{pi_id[:8].upper()}'} · {amount_display}",
#                     html_body=html_body,
#                     pdf_bytes=pdf_bytes,
#                     pdf_filename=f"invoice_{pi_id[:8].upper()}.pdf",
#                 )
#                 # print(f"📧 Invoice emailed to {customer_email}")
#             except Exception as e:
#                 print(f"Email send failed: {e}")


#     elif event["type"] == "payment_intent.payment_failed":
#         intent = event["data"]["object"]
#         invoice_id = (intent.get("metadata") or {}).get("invoice_id")
#         print(f"Payment failed for invoice {invoice_id}")

    # Respond 200 to acknowledge receipt only needed by stripe to confirm
    # return {"status": "success"}
#------------S Bibhishika----------------
from utils.imageupload import upload_image_and_get_url


@custom_router.post("/public_upload_image")
async def public_upload_image(file: UploadFile = File(...)):
    current_user=Depends(get_current_active_user),
    try:
        # Get the file suffix
        suffix = Path(file.filename).suffix

        # Save temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Upload and get public URL
        public_url = upload_image_and_get_url(tmp_path)

        # Remove temp file
        os.remove(tmp_path)

        if not public_url:
            raise HTTPException(status_code=500, detail="Failed to generate public URL")

        return {"image_url": public_url}

    except Exception as e:
        print(f"Error in public_upload_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

#------------E Bibhishika----------------
@custom_router.get("/version_build")
def version():
    return {"version : 1.0.2"}

@custom_router.put("/update_views/{listing_id}")
def update_listing_views(
    listing_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user  # assuming current_user has user_id (UUID)
        print("Updating views for listing:", listing_id, "by user:", user_id)
        # 1️⃣ Check if the listing exists
        listing = (
            db.query(MODEL_REGISTRY["listings"]["model"])
            .filter_by(id=listing_id)
            .first()
        )
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        # 2️⃣ Check if this user has already viewed this listing
        view_exists = (
            db.query(MODEL_REGISTRY["views_tracking"]["model"])
            .filter_by(user_id=user_id, listings_id=listing_id)
            .first()
        )

        # 3️⃣ If not viewed yet, insert into views_tracking and increment views
        if not view_exists:
            # Insert a new record in views_tracking
            new_view = MODEL_REGISTRY["views_tracking"]["model"](
                user_id=user_id, listings_id=listing_id
            )
            db.add(new_view)

            # Increment the views count in listings
            if listing.views is None:
                listing.views = 1
            else:
                listing.views += 1

            db.commit()
            db.refresh(listing)

            return {
                "status_code": 200,
                "detail": f"First view recorded. Total views: {listing.views}",
            }

        # 4️⃣ If already viewed, skip increment
        else:
            return {
                "status_code": 200,
                "detail": "User has already viewed this listing. Views not incremented.",
            }

    except Exception as e:
        db.rollback()
        print(f"Error updating views for listing {listing_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error updating views: {str(e)}")


@custom_router.get("/listings", response_model=List[ListingOut])
def get_listings(
    sort: Literal["newest", "price_asc", "price_desc"] = Query("newest"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_square_feet: Optional[int] = None,
    max_square_feet: Optional[int] = None,
    bedrooms: Optional[int] = None,
    # Location params
    lat: Optional[float] = Query(None, description="Latitude for radius filter"),
    lng: Optional[float] = Query(None, description="Longitude for radius filter"),
    radius_km: float = Query(5.0, ge=0.1, le=100.0, description="Radius in km"),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    # ⬇️ Optional auth: implement `get_optional_user` separately; it should return user_id or None.
    user_id: Optional[str] = Depends(get_optional_user),
    location_name: Optional[str] = Query(None, description="Location name search")
):
    sql = text("""
        SELECT
          l.id, l.title, l.price, l.status, l.views, l.created_at,
          l.contact_name, l.contact_number, l.location, l.latitude, l.longitude,
          s.space_type, s.bedroom, s.bathroom, s.kitchen, s.square_feet, s.living_room, s.details,
          COALESCE(
            ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL AND i.image_url <> ''),
            ARRAY[]::varchar[]
          ) AS images,
          CASE
            WHEN :lat IS NULL OR :lng IS NULL OR l.latitude IS NULL OR l.longitude IS NULL THEN NULL
            ELSE 2 * 6371 * ASIN(
              SQRT(
                POWER(SIN(RADIANS((l.latitude - :lat) / 2)), 2) +
                COS(RADIANS(:lat)) * COS(RADIANS(l.latitude)) *
                POWER(SIN(RADIANS((l.longitude - :lng) / 2)), 2)
              )
            )
          END AS distance_km,
          /* Favorite info for this caller (NULL/false if public) */
          BOOL_OR(f.id IS NOT NULL) AS is_favorite,
          MAX(f.id)                 AS favorite_id,
          MAX(f.created_at)         AS favorite_created_at
        FROM listings l
        LEFT JOIN listing_space s ON s.listing_id = l.id
        LEFT JOIN image i        ON i.listing_id = l.id
        /* Only join favorites for this user so grouping remains tidy */
        LEFT JOIN favorites f
               ON f.listing_id = l.id
              AND :user_id IS NOT NULL
              AND f.user_id = :user_id
        WHERE l.status = 'active'
          AND (:min_price IS NULL OR l.price >= :min_price)
          AND (:max_price IS NULL OR l.price <= :max_price)
          AND (:min_sqft  IS NULL OR s.square_feet >= :min_sqft)
          AND (:max_sqft  IS NULL OR s.square_feet <= :max_sqft)
          AND (:bedrooms  IS NULL OR s.bedroom     >= :bedrooms)
            AND(
               (:location_name IS NULL OR l.location ILIKE '%' || :location_name|| '%')
            AND (
                :lat IS NULL OR :lng IS NULL
            OR (
              l.latitude IS NOT NULL AND l.longitude IS NOT NULL
              AND 2 * 6371 * ASIN(
                    SQRT(
                      POWER(SIN(RADIANS((l.latitude - :lat) / 2)), 2) +
                      COS(RADIANS(:lat)) * COS(RADIANS(l.latitude)) *
                      POWER(SIN(RADIANS((l.longitude - :lng) / 2)), 2)
                    )
                  ) <= :radius_km
            )
          )
        )
        GROUP BY
          l.id, l.title, l.price, l.status, l.views, l.created_at,
          l.contact_name, l.contact_number, l.location, l.latitude, l.longitude,
          s.space_type, s.bedroom, s.bathroom, s.kitchen, s.square_feet, s.living_room, s.details
        ORDER BY
          CASE WHEN :sort = 'price_asc'  THEN l.price END ASC,
          CASE WHEN :sort = 'price_desc' THEN l.price END DESC,
          CASE WHEN :sort = 'newest'     THEN l.created_at END DESC,
          l.id
        OFFSET :offset LIMIT :limit;
    """)

    params = {
        "min_price": min_price,
        "max_price": max_price,
        "min_sqft": min_square_feet,
        "max_sqft": max_square_feet,
        "bedrooms": bedrooms,
        "sort": sort,
        "lat": lat,
        "lng": lng,
        "radius_km": radius_km,
        "offset": (page - 1) * page_size,
        "limit": page_size,
        "user_id": user_id,  # None for public calls; actual UUID/str for logged-in users
        "location_name": location_name,
    }

    rows = db.execute(sql, params).mappings().all()

    out: List[ListingOut] = []
    for r in rows:
        out.append(ListingOut(
            id=r["id"],
            title=r["title"],
            price=float(r["price"]) if r["price"] is not None else 0.0,
            status=r["status"],
            views=r["views"],
            created_at=r["created_at"],
            contact_name=r["contact_name"],
            contact_number=str(r["contact_number"]) if r["contact_number"] is not None else "",
            location=r["location"],
            latitude=float(r["latitude"]) if r["latitude"] is not None else None,
            longitude=float(r["longitude"]) if r["longitude"] is not None else None,
            space_type=r["space_type"],
            bedrooms=int(r["bedroom"]) if r["bedroom"] is not None else None,
            bathroom=int(r["bathroom"]) if r["bathroom"] is not None else None,
            kitchen=int(r["kitchen"]) if r["kitchen"] is not None else None,
            square_feet=int(r["square_feet"]) if r["square_feet"] is not None else None,
            living_room=int(r["living_room"]) if r["living_room"] is not None else None,
            images=list(r["images"] or []),
            details=r["details"],
            distance_km=float(r["distance_km"]) if r.get("distance_km") is not None else None,
            is_favorite=bool(r["is_favorite"]),
            favorite_id=int(r["favorite_id"]) if r["favorite_id"] is not None else None,
            favorite_created_at=r["favorite_created_at"],
        ))

    return out

@custom_router.get("/favourites", response_model=List[ListingOut])
def get_favourites(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    # Use UUID directly if current_user is already the UUID
    user_id = getattr(current_user, "user_id", current_user)

    sql = text("""
        SELECT
          l.id,
          l.title,
          l.price,
          l.status,
          l.views,
          l.created_at,
          l.contact_name,
          l.contact_number,
          l.location,
          l.latitude,
          l.longitude,

          -- Aggregate per-listing space info
          MAX(s.space_type)   AS space_type,
          MAX(s.bedroom)      AS bedroom,
          MAX(s.bathroom)     AS bathroom,
          MAX(s.kitchen)      AS kitchen,
          MAX(s.square_feet)  AS square_feet,
          MAX(s.living_room)  AS living_room,
          MAX(s.details)      AS details,

          -- Aggregate images
          COALESCE(
            ARRAY_AGG(DISTINCT i.image_url)
              FILTER (WHERE i.image_url IS NOT NULL AND i.image_url <> ''),
            ARRAY[]::varchar[]
          ) AS images,

          -- Favourite metadata for this user
          MAX(f.id)          AS favorite_id,
          TRUE               AS is_favorite,
          MAX(f.created_at)  AS favorite_created_at

        FROM favorites f
        JOIN listings l
          ON l.id = f.listing_id
        LEFT JOIN listing_space s
          ON s.listing_id = l.id
        LEFT JOIN image i
          ON i.listing_id = l.id
        WHERE f.user_id = :user_id
          AND l.status = 'active'
        GROUP BY
          l.id, l.title, l.price, l.status, l.views, l.created_at,
          l.contact_name, l.contact_number, l.location, l.latitude, l.longitude
        ORDER BY MAX(f.created_at) DESC, l.id DESC
        OFFSET :offset LIMIT :limit;
    """)

    params = {
        "user_id": user_id,
        "offset": (page - 1) * page_size,
        "limit": page_size,
    }

    rows = db.execute(sql, params).mappings().all()

    out: List[ListingOut] = []
    for r in rows:
        out.append(ListingOut(
            id=r["id"],
            title=r["title"],
            price=float(r["price"]) if r["price"] is not None else 0.0,
            status=r["status"],
            views=r["views"],
            created_at=r["created_at"],
            contact_name=r["contact_name"],
            contact_number=str(r["contact_number"]) if r["contact_number"] is not None else "",
            location=r["location"],
            latitude=float(r["latitude"]) if r["latitude"] is not None else None,
            longitude=float(r["longitude"]) if r["longitude"] is not None else None,
            space_type=r["space_type"],
            bedrooms=int(r["bedroom"]) if r["bedroom"] is not None else None,
            bathroom=int(r["bathroom"]) if r["bathroom"] is not None else None,
            kitchen=int(r["kitchen"]) if r["kitchen"] is not None else None,
            square_feet=int(r["square_feet"]) if r["square_feet"] is not None else None,
            living_room=int(r["living_room"]) if r["living_room"] is not None else None,
            images=list(r["images"] or []),
            details=r["details"],
            distance_km=None,  # not applicable for favourites

            is_favorite=bool(r.get("is_favorite", True)),
            favorite_id=int(r["favorite_id"]) if r.get("favorite_id") is not None else None,
            favorite_created_at=r.get("favorite_created_at"),
        ))

    return out

# -------------------- S Rahul-------------------
@custom_router.get("/featured_listing")
def featured_listing(
    db: Session = Depends(get_db),
):
    l=Listing
    s=ListingSpace
    i=Image

    results = (
        db.query(
            l.id.label("listing_id"),
            l.title,
            l.price,
            s.bedroom,
            s.bathroom,
            func.array_agg(i.image_url).label("image_urls"),
        )
        .outerjoin(s, l.id== s.listing_id)
        .outerjoin(i, l.id == i.listing_id)
        .filter(l.status == "active")
        .group_by(l.id, l.title, l.price, s.bedroom, s.bathroom, l.created_at)
        .order_by(l.created_at.desc())
        .limit(4)
        .all()
    )
    # Convert results to list of dicts
    response = [dict(row._mapping) for row in results]
    return JSONResponse(content=jsonable_encoder(response))


# # ---------------- User Tracking For Nepal Community Web app----------------
# class UserTrackingCreate(BaseModel):
#     uuid_ip: Optional[str] = None
#     ip: Optional[str] = None
#     state: Optional[str] = None
#     city: Optional[str] = None
#     lat: Optional[float] = None
#     lon: Optional[float] = None

# class UserTrackingUpdate(BaseModel):
#     ip: Optional[str] = None
#     state: Optional[str] = None
#     city: Optional[str] = None
#     logged_counts: Optional[int] = None

# class FamilyNumberSubmittedCreate(BaseModel):
#     uuid_ip: str
#     family_number: int
#     state: str | None = None
#     city: str | None = None
#     is_verified: bool = False

# class CommunityInfoCreate(BaseModel):
#     state: str
#     title: str 
#     description: str 
#     url: str | None = None
#     is_active: bool = True 
#     is_verified: bool = False
#     email: str 
#     created_at: datetime | None = None
#     post_type_id: int | None = None
#     is_email_sent: bool = False
#     is_promote: bool = False

# class UserDeviceInfoCreate(BaseModel):
#     ip_uuid: str
#     device: str | None = None
#     os: str | None = None
#     browser: str | None = None
#     engine: str | None = None
#     cpu: str | None = None
#     app_version: str | None = None

# Simple token auth for these endpoints
def verify_token(token: str = Header(...)):
    if token != "mysecrettoken": 
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token

# GET: list users or get by uuid_ip
@custom_router.get("/userTracking")
def get_user_tracking(
    uuid_ip: Optional[str] = Query(None),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    query = db.query(UserVisitTracking)
    if uuid_ip:
        query = query.filter(UserVisitTracking.uuid_ip == uuid_ip)
    results = query.all()
    
    data = [{
        "id": r.id,
        "uuid_ip": r.uuid_ip,
        "ip": r.ip,
        "state": r.state,
        "city": r.city,
        "logged_counts": r.logged_counts,
        "lat": r.lat,
        "lon": r.lon
    } for r in results]
    
    return JSONResponse(content=jsonable_encoder(data))


# POST: create new user tracking
@custom_router.post("/userTracking")
def create_user_tracking(
    data: UserTrackingCreate,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    if not data.uuid_ip:
        raise HTTPException(status_code=400, detail="uuid_ip is required from frontend")

    existing = db.query(UserVisitTracking).filter(UserVisitTracking.uuid_ip == data.uuid_ip).first()
    if existing:
        raise HTTPException(status_code=400, detail="UserVisitTracking with this uuid_ip already exists")

    try:
        new_entry = UserVisitTracking(
            uuid_ip=data.uuid_ip,
            ip=data.ip,
            state=data.state,
            city=data.city,
            logged_counts=1,
            lat=data.lat,
            lon=data.lon
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        return jsonable_encoder({
            "id": new_entry.id,
            "uuid_ip": new_entry.uuid_ip,
            "ip": new_entry.ip,
            "state": new_entry.state,
            "city": new_entry.city,
            "logged_counts": new_entry.logged_counts,
            "lat": new_entry.lat,
            "lon": new_entry.lon
        })

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    

# PATCH: update user tracking by uuid_ip
@custom_router.patch("/userTracking/{uuid_ip}")
def update_user_tracking(
    uuid_ip: str,
    data: UserTrackingUpdate,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = db.query(UserVisitTracking).filter(UserVisitTracking.uuid_ip == uuid_ip).first()
    if not user:
        raise HTTPException(status_code=404, detail="UserVisitTracking not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return jsonable_encoder({
        "id": user.id,
        "uuid_ip": user.uuid_ip,
        "ip": user.ip,
        "state": user.state,
        "city": user.city,
        "logged_counts": user.logged_counts,
        "lat": user.lat,
        "lon": user.lon
    })

@custom_router.get("/familyCounts")
def get_family_counts(
    state: str = Query(..., description="State to filter family counts"),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Clean up the incoming state
    state_clean = state.strip().lower()

    # Case-insensitive and trim spaces in the database
    results = (
        db.query(FamilyCounts)
        .filter(func.lower(func.trim(FamilyCounts.state)) == state_clean)
        .all()
    )
    print("results:", results)

    return JSONResponse(content=[{
        "city": r.city,
        "state": r.state,
        "family_count": r.family_count,
        "is_active": r.is_active
    } for r in results])

@custom_router.get("/postTypes", response_model=List[PostTypeOutput])
def get_post_types(
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    results = db.query(PostType).all()

    return results


@custom_router.get("/communityInfo")
def get_community_info(
    state: str = Query(..., description="State to filter community info"),
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Clean up the incoming state
    state_clean = state.strip().lower()

    # Case-insensitive and trim spaces in the database
    results = (
        db.query(CommunityInfo)
        .filter(func.lower(func.trim(CommunityInfo.state)) == state_clean)
        .all()
    )
    print("results:", results)

    return JSONResponse(content=[{
        "id": r.id,
        "state": r.state,
        "title": r.title,
        "description": r.description,
        "url": r.url,
        "is_active": r.is_active,
        "is_verified": r.is_verified,
        "email": r.email,
        "created_at": r.created_at,
        "post_type_id": r.post_type_id,
        "is_email_sent": r.is_email_sent,
        "is_promote": r.is_promote
    } for r in results])

# POST: create new user_device info 
@custom_router.post("/userDeviceInfo", response_model = UserDeviceInfoOutput)
def create_user_device_info(
    data: UserDeviceInfoCreate,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    if not data.ip_uuid:
        raise HTTPException(status_code=400, detail="ip_uuid is required from frontend")

    try:
        new_entry = UserDeviceInfo(
            ip_uuid=data.ip_uuid,
            device=data.device,
            os=data.os,
            browser=data.browser,
            engine=data.engine,
            cpu=data.cpu,
            
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        
        return new_entry

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# POST: create new community Info 
@custom_router.post("/communityInfo", response_model=CommunityInfoOutput )
def create_community_info(
    data: CommunityInfoCreate,
    db: Session = Depends(get_db)
):
    if not data.state:
        raise HTTPException(status_code=400, detail="State is required from frontend")
    if not data.title:
        raise HTTPException(status_code=400, detail="Title is required from frontend")

    try:
        new_entry = CommunityInfo(
            state=data.state,
            title=data.title,
            description=data.description,
            url=data.url,
            email=data.email,
            created_at=data.created_at,
            post_type_id=data.post_type_id,

        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        
        return new_entry

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Integrity error")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# ---------- Global Cache ----------
city_state_cache: list[dict] | None = None  # starts empty

def load_city_states(
    db: Session = Depends(get_db)
)-> list[dict]:
    print("---loading from db")
    try:
        results = (
            db.query(CityState).with_entities(CityState.id, CityState.city, CityState.state_abbr)
            .all()
        )
        return [{"id": r.id, "city": r.city, "state_abbr": r.state_abbr,"city_state": f"{r.city}, {r.state_abbr}"} for r in results]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@custom_router.post("/refresh-cache")
def refresh_city_cache(token: str = Depends(verify_token),db: Session = Depends(get_db)):
    load_city_states(db)
    return {"message": "City cache refreshed"}

@custom_router.get("/city_states",response_model=List[CityStateOutput])
def get_city_states(
    city: str = Query(..., description="City name or part of it for search"),
    # token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        global city_state_cache
        if city_state_cache is None:
            city_state_cache = load_city_states(db)
        q_lower = city.lower()
        results = [
            city for city in city_state_cache if q_lower in city["city_state"].lower()
        ][:5]
        return results

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@custom_router.post("/familyNumberSubmitted")
def family_number_submitted(
    data: FamilyNumberSubmittedCreate,
    token: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:
        # Check if uuid_ip already exists
        existing = db.query(FamilyNumberSubmitted).filter_by(uuid_ip=data.uuid_ip).first()
        if existing:
            raise HTTPException(status_code=400, detail="UUID already exists")

        # Create and save record
        new_entry = FamilyNumberSubmitted(
            uuid_ip=data.uuid_ip,
            state=data.state,
            city=data.city,
            family_number=data.family_number,
            is_verified=data.is_verified
        )

        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        return JSONResponse(
            status_code=201,
            content={
                "message": "Family number submitted successfully",
                "data": {
                    "uuid_ip": new_entry.uuid_ip,
                    "state": new_entry.state,
                    "city": new_entry.city,
                    "family_number": new_entry.family_number,
                    "is_verified": new_entry.is_verified,
                    "created_at": str(new_entry.created_at)
                }
            }
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))