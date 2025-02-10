from werkzeug.security import generate_password_hash

admin_password = "Admin@1"
hashed_password = generate_password_hash(admin_password)
print("Hashed Password:", hashed_password)
