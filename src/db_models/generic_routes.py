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
router = APIRouter(prefix="/generic")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from src.db_models.generic_models import AppMinimumVersion, Invoice, Listing, ListingSpace, Subscription, Image
from src.db_models.generic_schemas import AppVersionResponse, ListingOut

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




### - check if user exist or not  -- this need to be chnaged later 
from src.db_models.generic_models import UserProfile
from uuid import UUID
@router.get("/user_profile/exists")
def check_user_profile_exists(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    exists = db.query(UserProfile).filter(UserProfile.user_id == user_id).first() is not None
    return JSONResponse(content={"isValid": exists})

from pathlib import Path as SysPath
custom_router = APIRouter(prefix="/custom")

# Mukesh Payment route
# Secrete key
class PaymentIntentRequest(BaseModel):
    amount: int   # Stripe expects integer (e.g., 1000 = 10.00 GBP)
    currency: str
    plan_name: str
    # user_id : str
stripe.api_key = os.getenv("STRIPE_API_KEY") 
WEBHOOK_SECRET = "whsec_Hrk6iWEnpB8K8pihIapTjHYedBoZ3FAw" # Global sandbox key
# WEBHOOK_SECRET = "whsec_65de4521913b6fa18691fa43eee81078c9cb94367477bd449ecd779ce4ea81a0"
#Local key
@custom_router.post("/create-payment-intent")
def create_payment_intent(data: PaymentIntentRequest,
                          current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
    ):
    try:
        #Creating invoice in database
        new_invoice = Invoice(
            user_id=current_user,   
            # subscription_id=data.subscription_id,  
            plan_name = data.plan_name,
            amount=data.amount / 100.0,     # store as dollars instead of cents
            paid=False
        )
        db.add(new_invoice)
        db.commit()
        db.refresh(new_invoice)
        
        # Create payment intent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=data.amount,
            currency=data.currency,
            automatic_payment_methods={"enabled": True},
            metadata = {
                "user_id":current_user,
                "plan_name": data.plan_name,
                "invoice_id": str(new_invoice.id)
            }
        )
        # print(f"Inside create payment intent with invoice id:{new_invoice.id}")
        return {"client_secret": intent.client_secret, "invoice_id": new_invoice.id}
    except Exception as e:
        print(f"Error details for payment0intent {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))



def format_amount_for_email(amount_minor: int, currency: str) -> str:
    c = currency.upper()
    if c in ZERO_DECIMAL:
        return f"{c} {amount_minor:,.0f}"
    return f"{c} {amount_minor/100:,.2f}"
ZERO_DECIMAL = {"BIF","CLP","DJF","GNF","JPY","KMF","KRW","MGA","PYG","RWF","UGX","VND","VUV","XAF","XOF","XPF"}
@custom_router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    raw_payload: bytes = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=raw_payload.decode("utf-8"),
            sig_header=sig_header,
            secret=WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # --- Handle events ---
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]  
        # Common fields
        pi_id = intent["id"]
        currency = (intent.get("currency") or "usd").upper()
        is_zero_decimal = currency in ZERO_DECIMAL

        # Prefer amount_received; fall back to amount
        amount_minor = intent.get("amount_received") or intent.get("amount") or 0
        amount_major = amount_minor if is_zero_decimal else amount_minor / 100.0

        # Metadata (optional but super useful)
        md = intent.get("metadata", {}) or {}
        user_id = md.get("user_id")
        invoice_id = md.get("invoice_id")
        plan_name = md.get("plan_name") or intent.get("description") or "Subscription"
        quantity = None
        try:
            if md.get("quantity"):
                quantity = float(md["quantity"])
        except Exception:
            quantity = None
        unit = md.get("unit")  # e.g., "months", "seats"

        # print(f"payment succeeded for user {user_id}, invoice {invoice_id}, amount {amount_major} {currency}")

        # --- Mark invoice paid in your DB ---
        if invoice_id:
            inv = db.query(Invoice).filter(Invoice.id == int(invoice_id)).first()
            if inv:
                inv.paid = True
                db.commit()

        # --- Extend subscription by 30 days ---
        if user_id:
            sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
            if sub:
                now_utc = datetime.now(timezone.utc)

                end = sub.end_date
                if end is not None:
                    if end.tzinfo is None:
                        end = end.replace(tzinfo=timezone.utc)

                if end and end > now_utc:
                    sub.end_date = end + timedelta(days=30)
                else:
                    sub.end_date = now_utc + timedelta(days=30)

                sub.status = "active"
                sub.plan_id = 1
                db.commit()
                print(f"📌 Subscription for user {user_id} extended until {sub.end_date}")

        customer_name = ""
        customer_email = ""

        try:
            user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if user:
                customer_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
                customer_email = (user.email or "").strip()
        except Exception as e:
            print(f"error in name details {e}")
            pass
        
        print(f"Customer name: {customer_name}")
        # Fallback to charge billing_details if needed
        charge = None
        try:
            charges = intent.get("charges", {}).get("data", [])
            if charges:
                charge = charges[0]
                if not customer_email:
                    customer_email = (charge.get("billing_details", {}).get("email") or "").strip()
                if not customer_name:
                    customer_name = (charge.get("billing_details", {}).get("name") or "").strip()
        except Exception:
            pass

        # Stripe receipt URL (handy to include in invoice PDF as a “paid via Stripe” link)
        receipt_url = ""
        if charge:
            receipt_url = (charge.get("receipt_url") or "").strip()

        # --- Company / biller info - can be fetched from database if needed
        company_name = "Neogenxai Pvt. Ltd."
        company_location = "Bhaktapur, Nepal"
        company_email = "itadmin@neogenxai.com"
        phone_number = "+977 9762656555"


        issue_dt_local = datetime.now(ZoneInfo("Asia/Kathmandu")).replace(tzinfo=None)  # your generator expects naive
        # out_path = os.path.join("invoices", f"invoice_{pi_id}.pdf")
        os.makedirs("invoices", exist_ok=True)


        pdf_bytes = generate_invoice_pdf(
            customer_name=customer_name or "Customer",
            customer_email=customer_email or "unknown@example.com",
            amount=float(amount_major),
            plan_name=plan_name,
            quantity=quantity,                 
            unit=unit,                         
            company_name=company_name,
            company_location=company_location,
            company_email=company_email,
            phone_number=phone_number,
            currency=currency,
            invoice_number=md.get("invoice_number") or f"INV-{pi_id[:8].upper()}",
            issue_date=issue_dt_local,
            due_days=0,                        
            stripe_payment_url=receipt_url,    # links to Stripe’s receipt
            # output_path=out_path,
        )
        # print(f"🧾 Invoice PDF saved to {pdf_path}")
        
        amount_display = format_amount_for_email(amount_minor, currency)

        html_body = build_invoice_html(
            customer_name=customer_name or "Customer",
            customer_email=customer_email or "unknown@example.com",
            plan_name=plan_name,
            currency=currency,
            amount=float(amount_major),                
            quantity=quantity,                         
            unit=unit,                                
            invoice_number=md.get("invoice_number") or f"INV-{pi_id[:8].upper()}",
            issue_date_yyyy_mm_dd=issue_dt_local.strftime("%Y-%m-%d"),
            due_date_yyyy_mm_dd=issue_dt_local.strftime("%Y-%m-%d"), 
            receipt_url=receipt_url or None,
            company_name="Neogenxai Pvt. Ltd.",
            company_location="Bhaktapur, Nepal",
            company_email="itadmin@neogenxai.com",
            phone_number="+977 9762656555",
        )

        if customer_email:
            try:
                send_invoice_email(
                    to_email=customer_email,
                    subject=f"Your Invoice {md.get('invoice_number') or f'INV-{pi_id[:8].upper()}'} · {amount_display}",
                    html_body=html_body,
                    pdf_bytes=pdf_bytes,
                    pdf_filename=f"invoice_{pi_id[:8].upper()}.pdf",
                )
                # print(f"📧 Invoice emailed to {customer_email}")
            except Exception as e:
                print(f"Email send failed: {e}")


    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        invoice_id = (intent.get("metadata") or {}).get("invoice_id")
        print(f"Payment failed for invoice {invoice_id}")

    # Respond 200 to acknowledge receipt only needed by stripe to confirm
    return {"status": "success"}
#------------S Bibhishika----------------
from utils.imageupload import upload_image_and_get_url


@custom_router.post("/public_upload_image")
async def public_upload_image(file: UploadFile = File(...)):
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
        listing = db.query(MODEL_REGISTRY["listings"]["model"]).filter_by(id=listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        if listing.views is None:
            listing.views = 1
        else:
            listing.views += 1

        db.commit()
        db.refresh(listing)
        return {"status_code": 200, "detail": f"Views updated to {listing.views}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating views: {str(e)}")

@custom_router.get("/listings", response_model=List[ListingOut])
def get_listings(
    sort: Literal["newest", "price_asc", "price_desc"] = Query("newest"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_square_feet: Optional[int] = None,
    max_square_feet: Optional[int] = None,
    bedrooms: Optional[int] = None,
    # 👇 NEW: location params
    lat: Optional[float] = Query(None, description="Latitude for radius filter"),
    lng: Optional[float] = Query(None, description="Longitude for radius filter"),
    radius_km: float = Query(5.0, ge=0.1, le=100.0, description="Radius in km"),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    
    sql = text("""
            SELECT
            l.id, l.title, l.price, l.status, l.views, l.created_at,
            l.contact_name, l.contact_number, l.location, l.latitude, l.longitude,
            s.space_type, s.bedroom, s.bathroom, s.kitchen, s.square_feet, s.living_room,s.details,
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
            END AS distance_km
            FROM listings l
            LEFT JOIN listing_space s ON s.listing_id = l.id
            LEFT JOIN image i ON i.listing_id = l.id
            WHERE l.status = 'active'
            AND (:min_price IS NULL OR l.price >= :min_price)
            AND (:max_price IS NULL OR l.price <= :max_price)
            AND (:min_sqft IS NULL OR s.square_feet >= :min_sqft)
            AND (:max_sqft IS NULL OR s.square_feet <= :max_sqft)
            AND (:bedrooms IS NULL OR s.bedroom >= :bedrooms)
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
        "radius_km": radius_km,  # defaults to 5.0 if not provided
        "offset": (page - 1) * page_size,
        "limit": page_size,
    }

    rows = db.execute(sql, params).mappings().all()

    out: List[ListingOut] = []
    for r in rows:
        out.append(ListingOut(
            id=r["id"],
            title=r["title"],
            # description=r["description"],
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
            distance_km=float(r["distance_km"]) if "distance_km" in r and r["distance_km"] is not None else None,
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