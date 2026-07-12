# Environment and Security Policy

| Environment | Demo | OpenAPI/docs | Detailed system status | Database |
|---|---|---|---|---|
| local | explicitly configured only | enabled for local development | authenticated admin | V2-only local development |
| test | disabled by default | test-controlled | authenticated admin | V2-only test |
| staging | prohibited | disabled | authenticated admin | V2-only staging |
| production | prohibited | disabled | authenticated admin | V2-only production |

The only public system endpoints are health, live, and readiness. Business mutation requires backend-enforced manager or admin permissions. V2 never uses wildcard production CORS, startup demo seeding, public OpenAPI/docs, optional-auth approval mutation, or frontend-only authorization.
