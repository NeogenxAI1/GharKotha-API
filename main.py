from fastapi import FastAPI
from src.db_models.generic_routes import router as generic_routers, custom_router
from core.database import Base, engine
import atexit

#from src.db_models.generic_routes import custom_router as custom_query_router
Base.metadata.create_all(bind=engine, checkfirst=True)

app = FastAPI()
app.include_router(generic_routers)
app.include_router(custom_router)



#app.include_router(custom_query_router, prefix="/report", tags=["Report"])
