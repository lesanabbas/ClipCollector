from database import Base, engine
from models import Download  # Import the model(s) you want to create tables for

# Create all tables in the database
Base.metadata.create_all(bind=engine)

print("Tables created successfully!")
