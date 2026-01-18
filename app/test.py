from jose import jwt
a = jwt.encode({
    "user": "alice",
    "main": "data",
    "phone": 4594590,
    "password": "gemini is gay"
}, "secret_key")
b = jwt.get_unverified_claims(a)
c = jwt.decode(a.encode(encoding="utf-8"), key="secret_key", algorithms="HS256")


print(a)
print(b)
print(c)