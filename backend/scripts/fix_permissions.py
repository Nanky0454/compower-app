from app import create_app, db
from app.models.role import Role
from app.models.permission import Permission

app = create_app()

with app.app_context():
    print("--- Fixing Permissions ---")
    
    # 1. Ensure Permissions Exist
    perms = ['view:treasury', 'manage:treasury']
    for p_name in perms:
        p = Permission.query.filter_by(name=p_name).first()
        if not p:
            print(f"Creating permission: {p_name}")
            db.session.add(Permission(name=p_name, display_name=p_name, description='Fixed by script'))
        else:
            print(f"Permission exists: {p_name}")
    db.session.commit()

    # 2. Assign to Roles
    roles_to_fix = ['Admin', 'Usuario']
    for r_name in roles_to_fix:
        role = Role.query.filter_by(name=r_name).first()
        if not role:
            print(f"Role not found: {r_name}")
            continue
        
        print(f"Updating role: {r_name}")
        current_perms = set(p.name for p in role.permissions)
        
        for p_name in perms:
            if p_name not in current_perms:
                print(f"  Adding {p_name} to {r_name}")
                perm_obj = Permission.query.filter_by(name=p_name).first()
                role.permissions.append(perm_obj)
        
        db.session.commit()
        
    # 3. Verify
    print("\n--- Verification ---")
    for r in Role.query.all():
        print(f"Role: {r.name}")
        print(f"  Permissions: {[p.name for p in r.permissions]}")

    print("\nDone.")
