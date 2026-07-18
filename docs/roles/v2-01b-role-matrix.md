# V2-01B Role Matrix

| Operation | Anonymous | Viewer | Manager | Admin |
|---|---|---|---|---|
| Health/live/ready | allowed | allowed | allowed | allowed |
| Login | allowed | allowed | allowed | allowed |
| Current user | denied | own identity | own identity | own identity |
| Detailed system status | denied | denied | denied | allowed |
| First-user CLI | denied | denied | denied | explicit local operator command only |
| Business mutation | not implemented | not implemented | not implemented | not implemented |

Roles are enforced by FastAPI dependencies and the active database user, not by frontend visibility. Inactive users are denied even when a previously issued token is presented.
