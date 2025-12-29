"""
Seed script to populate database with sample advocates.
Run with: python seed_data.py
"""

import asyncio
from decimal import Decimal
from app.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.advocate_profile import AdvocateProfile, FeeCategory
from app.utils.security import get_password_hash


SAMPLE_ADVOCATES = [
    {
        "user": {
            "email": "rajesh.sharma@example.com",
            "password": "advocate123",
            "full_name": "Adv. Rajesh Kumar Sharma",
            "phone": "+91-98765-43210"
        },
        "profile": {
            "enrollment_number": "D/1234/2005",
            "enrollment_year": 2005,
            "bar_council": "Bar Council of Delhi",
            "states": ["Delhi", "Haryana", "Punjab"],
            "districts": ["Central Delhi", "South Delhi", "Gurugram"],
            "home_court": "Delhi High Court",
            "primary_specializations": ["civil", "constitutional", "property"],
            "sub_specializations": ["Writ Petitions", "Land Acquisition", "RERA"],
            "experience_years": 19,
            "landmark_cases": "12 reported judgments in property and constitutional matters",
            "success_rate": Decimal("85.5"),
            "current_case_load": 28,
            "max_case_capacity": 40,
            "fee_category": FeeCategory.PREMIUM,
            "consultation_fee": Decimal("5000"),
            "languages": ["Hindi", "English", "Punjabi"],
            "office_address": "Chamber No. 215, Delhi High Court, New Delhi",
            "rating": Decimal("4.8"),
            "review_count": 156,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "priya.mehta@example.com",
            "password": "advocate123",
            "full_name": "Adv. Priya Mehta",
            "phone": "+91-98765-12345"
        },
        "profile": {
            "enrollment_number": "MH/5678/2012",
            "enrollment_year": 2012,
            "bar_council": "Bar Council of Maharashtra and Goa",
            "states": ["Maharashtra", "Goa"],
            "districts": ["Mumbai City", "Mumbai Suburban", "Thane", "Pune"],
            "home_court": "Bombay High Court",
            "primary_specializations": ["matrimonial", "criminal", "civil"],
            "sub_specializations": ["Divorce", "Domestic Violence", "Maintenance", "Bail"],
            "experience_years": 12,
            "landmark_cases": "5 reported judgments in matrimonial matters",
            "success_rate": Decimal("82.0"),
            "current_case_load": 22,
            "max_case_capacity": 35,
            "fee_category": FeeCategory.STANDARD,
            "consultation_fee": Decimal("2000"),
            "languages": ["Hindi", "English", "Marathi", "Gujarati"],
            "office_address": "Office 401, Lawyers Tower, Fort, Mumbai",
            "rating": Decimal("4.6"),
            "review_count": 98,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "m.hussain@example.com",
            "password": "advocate123",
            "full_name": "Adv. Mohammed Hussain",
            "phone": "+91-98765-67890"
        },
        "profile": {
            "enrollment_number": "KA/2345/2008",
            "enrollment_year": 2008,
            "bar_council": "Bar Council of Karnataka",
            "states": ["Karnataka", "Tamil Nadu", "Kerala"],
            "districts": ["Bangalore Urban", "Bangalore Rural", "Chennai"],
            "home_court": "Karnataka High Court",
            "primary_specializations": ["criminal", "civil", "constitutional"],
            "sub_specializations": ["Bail Applications", "Section 138 NI Act", "Anticipatory Bail"],
            "experience_years": 16,
            "landmark_cases": "8 reported judgments in criminal matters",
            "success_rate": Decimal("88.0"),
            "current_case_load": 30,
            "max_case_capacity": 40,
            "fee_category": FeeCategory.STANDARD,
            "consultation_fee": Decimal("3000"),
            "languages": ["English", "Kannada", "Tamil", "Hindi", "Urdu"],
            "office_address": "Chamber No. 112, Karnataka High Court, Bangalore",
            "rating": Decimal("4.7"),
            "review_count": 134,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "sunita.devi@example.com",
            "password": "advocate123",
            "full_name": "Adv. Sunita Devi",
            "phone": "+91-98765-11111"
        },
        "profile": {
            "enrollment_number": "UP/8901/2015",
            "enrollment_year": 2015,
            "bar_council": "Bar Council of Uttar Pradesh",
            "states": ["Uttar Pradesh", "Uttarakhand"],
            "districts": ["Lucknow", "Kanpur", "Allahabad", "Varanasi"],
            "home_court": "Allahabad High Court",
            "primary_specializations": ["property", "conveyancing", "civil"],
            "sub_specializations": ["Sale Deeds", "Partition", "Title Disputes", "Will Probate"],
            "experience_years": 9,
            "landmark_cases": "2 reported judgments",
            "success_rate": Decimal("75.0"),
            "current_case_load": 18,
            "max_case_capacity": 30,
            "fee_category": FeeCategory.AFFORDABLE,
            "consultation_fee": Decimal("1000"),
            "languages": ["Hindi", "English"],
            "office_address": "Advocates Complex, Civil Lines, Lucknow",
            "rating": Decimal("4.3"),
            "review_count": 67,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "arjun.nair@example.com",
            "password": "advocate123",
            "full_name": "Adv. Arjun Nair",
            "phone": "+91-98765-22222"
        },
        "profile": {
            "enrollment_number": "KL/6789/2010",
            "enrollment_year": 2010,
            "bar_council": "Bar Council of Kerala",
            "states": ["Kerala", "Karnataka"],
            "districts": ["Ernakulam", "Thiruvananthapuram", "Kozhikode"],
            "home_court": "Kerala High Court",
            "primary_specializations": ["civil", "property", "conveyancing"],
            "sub_specializations": ["Land Disputes", "Partition Suits", "Injunctions"],
            "experience_years": 14,
            "landmark_cases": "6 reported judgments",
            "success_rate": Decimal("80.0"),
            "current_case_load": 25,
            "max_case_capacity": 35,
            "fee_category": FeeCategory.STANDARD,
            "consultation_fee": Decimal("2500"),
            "languages": ["English", "Malayalam", "Hindi", "Tamil"],
            "office_address": "High Court Advocates Block, Ernakulam, Kochi",
            "rating": Decimal("4.5"),
            "review_count": 89,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "deepika.rathore@example.com",
            "password": "advocate123",
            "full_name": "Adv. Deepika Singh Rathore",
            "phone": "+91-98765-33333"
        },
        "profile": {
            "enrollment_number": "RJ/3456/2016",
            "enrollment_year": 2016,
            "bar_council": "Bar Council of Rajasthan",
            "states": ["Rajasthan", "Madhya Pradesh"],
            "districts": ["Jaipur", "Jodhpur", "Udaipur"],
            "home_court": "Rajasthan High Court",
            "primary_specializations": ["matrimonial", "civil", "criminal"],
            "sub_specializations": ["Divorce", "Child Custody", "Maintenance", "DV Act"],
            "experience_years": 8,
            "landmark_cases": "3 reported judgments",
            "success_rate": Decimal("78.0"),
            "current_case_load": 20,
            "max_case_capacity": 30,
            "fee_category": FeeCategory.AFFORDABLE,
            "consultation_fee": Decimal("1500"),
            "languages": ["Hindi", "English", "Rajasthani"],
            "office_address": "Advocates Chambers, High Court Campus, Jaipur",
            "rating": Decimal("4.4"),
            "review_count": 56,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "vikram.choudhury@example.com",
            "password": "advocate123",
            "full_name": "Adv. Vikram Choudhury",
            "phone": "+91-98765-44444"
        },
        "profile": {
            "enrollment_number": "WB/4567/2000",
            "enrollment_year": 2000,
            "bar_council": "Bar Council of West Bengal",
            "states": ["West Bengal", "Jharkhand", "Odisha"],
            "districts": ["Kolkata", "Howrah", "North 24 Parganas"],
            "home_court": "Calcutta High Court",
            "primary_specializations": ["constitutional", "civil", "criminal"],
            "sub_specializations": ["PIL", "Writ Petitions", "Service Matters", "Land Acquisition"],
            "experience_years": 24,
            "landmark_cases": "18 reported judgments",
            "success_rate": Decimal("90.0"),
            "current_case_load": 32,
            "max_case_capacity": 40,
            "fee_category": FeeCategory.PREMIUM,
            "consultation_fee": Decimal("7500"),
            "languages": ["Bengali", "English", "Hindi"],
            "office_address": "Senior Advocates Block, Calcutta High Court, Kolkata",
            "rating": Decimal("4.9"),
            "review_count": 203,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "kavitha.reddy@example.com",
            "password": "advocate123",
            "full_name": "Adv. Kavitha Reddy",
            "phone": "+91-98765-55555"
        },
        "profile": {
            "enrollment_number": "TS/7890/2014",
            "enrollment_year": 2014,
            "bar_council": "Bar Council of Telangana",
            "states": ["Telangana", "Andhra Pradesh"],
            "districts": ["Hyderabad", "Rangareddy", "Secunderabad"],
            "home_court": "Telangana High Court",
            "primary_specializations": ["civil", "property", "constitutional"],
            "sub_specializations": ["RERA", "Real Estate Disputes", "Builder Disputes"],
            "experience_years": 10,
            "landmark_cases": "4 reported judgments",
            "success_rate": Decimal("76.0"),
            "current_case_load": 24,
            "max_case_capacity": 35,
            "fee_category": FeeCategory.STANDARD,
            "consultation_fee": Decimal("2000"),
            "languages": ["Telugu", "English", "Hindi"],
            "office_address": "Advocates Complex, High Court Road, Hyderabad",
            "rating": Decimal("4.4"),
            "review_count": 72,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "gurpreet.bedi@example.com",
            "password": "advocate123",
            "full_name": "Adv. Gurpreet Singh Bedi",
            "phone": "+91-98765-66666"
        },
        "profile": {
            "enrollment_number": "PB/5432/2011",
            "enrollment_year": 2011,
            "bar_council": "Bar Council of Punjab and Haryana",
            "states": ["Punjab", "Haryana", "Chandigarh"],
            "districts": ["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar"],
            "home_court": "Punjab and Haryana High Court",
            "primary_specializations": ["criminal", "civil", "property"],
            "sub_specializations": ["NDPS", "Bail", "Anticipatory Bail", "Murder Cases"],
            "experience_years": 13,
            "landmark_cases": "7 reported judgments",
            "success_rate": Decimal("84.0"),
            "current_case_load": 28,
            "max_case_capacity": 35,
            "fee_category": FeeCategory.STANDARD,
            "consultation_fee": Decimal("3500"),
            "languages": ["Punjabi", "Hindi", "English"],
            "office_address": "Sector 17, High Court Complex, Chandigarh",
            "rating": Decimal("4.6"),
            "review_count": 118,
            "is_verified": True,
            "is_available": True
        }
    },
    {
        "user": {
            "email": "fatima.khan@example.com",
            "password": "advocate123",
            "full_name": "Adv. Fatima Khan",
            "phone": "+91-98765-77777"
        },
        "profile": {
            "enrollment_number": "MP/2109/2017",
            "enrollment_year": 2017,
            "bar_council": "Bar Council of Madhya Pradesh",
            "states": ["Madhya Pradesh", "Chhattisgarh"],
            "districts": ["Bhopal", "Indore", "Jabalpur"],
            "home_court": "Madhya Pradesh High Court",
            "primary_specializations": ["matrimonial", "civil"],
            "sub_specializations": ["Muslim Personal Law", "Maintenance", "Mehr Recovery"],
            "experience_years": 7,
            "landmark_cases": "1 reported judgment",
            "success_rate": Decimal("72.0"),
            "current_case_load": 15,
            "max_case_capacity": 25,
            "fee_category": FeeCategory.AFFORDABLE,
            "consultation_fee": Decimal("1000"),
            "languages": ["Hindi", "English", "Urdu"],
            "office_address": "Advocates Building, M.P. High Court, Jabalpur",
            "rating": Decimal("4.2"),
            "review_count": 45,
            "is_verified": True,
            "is_available": True
        }
    }
]

# Sample client for testing
SAMPLE_CLIENT = {
    "email": "test.client@example.com",
    "password": "client123",
    "full_name": "Test Client",
    "phone": "+91-98765-00000"
}


async def seed_database():
    """Seed the database with sample data."""
    print("Initializing database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Create sample client
        print("Creating sample client...")
        client = User(
            email=SAMPLE_CLIENT["email"],
            password_hash=get_password_hash(SAMPLE_CLIENT["password"]),
            full_name=SAMPLE_CLIENT["full_name"],
            phone=SAMPLE_CLIENT["phone"],
            role=UserRole.CLIENT
        )
        db.add(client)

        # Create sample advocates
        print("Creating sample advocates...")
        for advocate_data in SAMPLE_ADVOCATES:
            # Create user
            user = User(
                email=advocate_data["user"]["email"],
                password_hash=get_password_hash(advocate_data["user"]["password"]),
                full_name=advocate_data["user"]["full_name"],
                phone=advocate_data["user"]["phone"],
                role=UserRole.ADVOCATE
            )
            db.add(user)
            await db.flush()  # Get user ID

            # Create profile
            profile_data = advocate_data["profile"].copy()
            profile_data["user_id"] = user.id
            profile = AdvocateProfile(**profile_data)
            db.add(profile)

            print(f"  Created: {user.full_name}")

        await db.commit()
        print("\nDatabase seeded successfully!")
        print(f"\nSample Client Login:")
        print(f"  Email: {SAMPLE_CLIENT['email']}")
        print(f"  Password: {SAMPLE_CLIENT['password']}")
        print(f"\nSample Advocate Login:")
        print(f"  Email: {SAMPLE_ADVOCATES[0]['user']['email']}")
        print(f"  Password: advocate123")


if __name__ == "__main__":
    asyncio.run(seed_database())
