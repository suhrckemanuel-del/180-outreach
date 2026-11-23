# 11 Shared registry on monday.com (when a second person does outreach)

**Problem.** Today only this kit sends, and it keeps its own list of who was contacted
(`state/registry.local.yaml`). As soon as another member writes to organisations, two people can
write to the same one.

**Do.** docs/setup.md step 4: a new board "Outreach registry" (Domain, Owner, Status, Last contact,
Blocked until), a token, the column ids into `tenant.yaml`, `registry.backend: monday`. Then copy the
local registry's rows onto the board once, and tell the branch: before you write to an organisation,
add its row.

**Note.** The monday code has not run against a real board. `python tools/registry.py test-monday` is
the first test.

**Done when.** A row added by hand on the board makes `registry.py check <domain>` say blocked.
