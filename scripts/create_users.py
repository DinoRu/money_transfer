"""
Script asynchrone pour créer les utilisateurs initiaux
- 1 Super Admin
- 2 Agents
- 3 Utilisateurs normaux
"""
import asyncio
import sys
from pathlib import Path

from src.db.session import AsyncSessionLocal

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession


from src.models.enums import UserRole
from src.services import user_service
from src.schemas.user import UserCreate


async def create_admin_user(db: AsyncSession) -> dict:
    """
    Crée le super administrateur
    
    Returns:
        Dictionnaire avec les informations de l'admin
    """
    admin_data = UserCreate(
        full_name="Super Administrator",
        email="admin@moneytransfer.com",
        phone="+79001234567",
        password="Admin123!@#",
        role=UserRole.ADMIN
    )
    
    try:
        existing = await user_service.get_by_email(db, admin_data.email)
        if existing:
            print(f"⚠️  Admin déjà existant: {admin_data.email}")
            return {
                "id": str(existing.id),
                "email": existing.email,
                "full_name": existing.full_name,
                "role": existing.role,
                "existed": True
            }
        
        admin = await user_service.create(db, admin_data)
        print(f"✅ Admin créé: {admin.email}")
        print(f"   Nom: {admin.full_name}")
        print(f"   Rôle: {admin.role}")
        print(f"   ID: {admin.id}")
        
        return {
            "id": str(admin.id),
            "email": admin.email,
            "full_name": admin.full_name,
            "role": admin.role,
            "password": "Admin123!@#",
            "existed": False
        }
    
    except Exception as e:
        print(f"❌ Erreur création admin: {e}")
        return None


async def create_agent_users(db: AsyncSession) -> list:
    """
    Crée les agents
    
    Returns:
        Liste des agents créés
    """
    agents_data = [
        UserCreate(
            full_name="Dmitry Volkov",
            email="dmitry.volkov@moneytransfer.com",
            phone="+79001234569",
            password="Agent123!",
            role=UserRole.AGENT
        ),
        UserCreate(
            full_name="Anna Sokolova",
            email="anna.sokolova@moneytransfer.com",
            phone="+79001234570",
            password="Agent123!",
            role=UserRole.AGENT
        )
    ]
    
    created_agents = []
    
    for agent_data in agents_data:
        try:
            existing = await user_service.get_by_email(db, agent_data.email)
            if existing:
                print(f"⚠️  Agent déjà existant: {agent_data.email}")
                created_agents.append({
                    "id": str(existing.id),
                    "email": existing.email,
                    "full_name": existing.full_name,
                    "role": existing.role,
                    "existed": True
                })
                continue
            
            agent = await user_service.create(db, agent_data)
            print(f"✅ Agent créé: {agent.email}")
            print(f"   Nom: {agent.full_name}")
            print(f"   Téléphone: {agent.phone}")
            print(f"   ID: {agent.id}")
            
            created_agents.append({
                "id": str(agent.id),
                "email": agent.email,
                "full_name": agent.full_name,
                "role": agent.role,
                "password": "Agent123!",
                "existed": False
            })
        
        except Exception as e:
            print(f"❌ Erreur création agent {agent_data.email}: {e}")
    
    return created_agents


async def create_normal_users(db: AsyncSession) -> list:
    """
    Crée les utilisateurs normaux
    
    Returns:
        Liste des utilisateurs créés
    """
    users_data = [
        UserCreate(
            full_name="Ivan Petrov",
            email="ivan.petrov@example.ru",
            phone="+79001234571",
            password="User123!",
            role=UserRole.USER
        ),
        UserCreate(
            full_name="Kofi Kouassi",
            email="kofi.kouassi@example.ci",
            phone="+2250707123456",
            password="User123!",
            role=UserRole.USER
        ),
        UserCreate(
            full_name="Amadou Diallo",
            email="amadou.diallo@example.sn",
            phone="+221771234567",
            password="User123!",
            role=UserRole.USER
        )
    ]
    
    created_users = []
    
    for user_data in users_data:
        try:
            existing = await user_service.get_by_email(db, user_data.email)
            if existing:
                print(f"⚠️  Utilisateur déjà existant: {user_data.email}")
                created_users.append({
                    "id": str(existing.id),
                    "email": existing.email,
                    "full_name": existing.full_name,
                    "role": existing.role,
                    "existed": True
                })
                continue
            
            user = await user_service.create(db, user_data)
            print(f"✅ Utilisateur créé: {user.email}")
            print(f"   Nom: {user.full_name}")
            print(f"   Téléphone: {user.phone}")
            print(f"   ID: {user.id}")
            
            created_users.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "password": "User123!",
                "existed": False
            })
        
        except Exception as e:
            print(f"❌ Erreur création utilisateur {user_data.email}: {e}")
    
    return created_users


async def main():
    """Fonction principale asynchrone"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "CRÉATION DES UTILISATEURS" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Initialiser la base de données
    print("\n🔧 Initialisation de la base de données...")
    # await init_db()
    print("✓ Base de données prête\n")
    
    # Créer une session asynchrone
    async with AsyncSessionLocal() as db:
        try:
            # 1. Super Admin
            print("=" * 80)
            print("👑 CRÉATION DU SUPER ADMIN")
            print("=" * 80)
            admin = await create_admin_user(db)
            await db.commit()
            
            # 2. Agents
            print("\n" + "=" * 80)
            print("👮 CRÉATION DES AGENTS")
            print("=" * 80)
            agents = await create_agent_users(db)
            await db.commit()
            
            # 3. Utilisateurs normaux
            print("\n" + "=" * 80)
            print("👥 CRÉATION DES UTILISATEURS")
            print("=" * 80)
            users = await create_normal_users(db)
            await db.commit()
            
            # Résumé
            print("\n" + "=" * 80)
            print("📊 RÉSUMÉ")
            print("=" * 80)
            
            total_created = 0
            total_existed = 0
            
            if admin:
                if not admin.get('existed'):
                    total_created += 1
                else:
                    total_existed += 1
                    
                print(f"\n✅ Super Admin:")
                print(f"   Email: {admin['email']}")
                if not admin.get('existed'):
                    print(f"   Mot de passe: Admin123!@#")
                print(f"   Rôle: {admin['role']}")
            
            if agents:
                agents_created = len([a for a in agents if not a.get('existed')])
                agents_existed = len([a for a in agents if a.get('existed')])
                total_created += agents_created
                total_existed += agents_existed
                
                print(f"\n✅ Agents: {len(agents)} au total")
                print(f"   Créés: {agents_created}")
                print(f"   Existants: {agents_existed}")
                for agent in agents:
                    if not agent.get('existed'):
                        print(f"\n   • {agent['full_name']}")
                        print(f"     Email: {agent['email']}")
                        print(f"     Mot de passe: Agent123!")
            
            if users:
                users_created = len([u for u in users if not u.get('existed')])
                users_existed = len([u for u in users if u.get('existed')])
                total_created += users_created
                total_existed += users_existed
                
                print(f"\n✅ Utilisateurs: {len(users)} au total")
                print(f"   Créés: {users_created}")
                print(f"   Existants: {users_existed}")
                for user in users:
                    if not user.get('existed'):
                        print(f"\n   • {user['full_name']}")
                        print(f"     Email: {user['email']}")
                        print(f"     Mot de passe: User123!")
            
            print(f"\n📈 Total: {total_created} créés, {total_existed} existants")
            
            # Commandes de connexion
            if total_created > 0:
                print("\n" + "=" * 80)
                print("🔑 COMMANDES DE CONNEXION (nouveaux utilisateurs)")
                print("=" * 80)
                
                if admin and not admin.get('existed'):
                    print("\n# Se connecter en tant qu'admin:")
                    print('curl -X POST http://localhost:8000/auth/login \\')
                    print('  -H "Content-Type: application/json" \\')
                    print('  -d \'{"email": "' + admin['email'] + '", "password": "Admin123!@#"}\'')
                
                for agent in agents:
                    if not agent.get('existed'):
                        print(f"\n# Se connecter en tant que {agent['full_name']}:")
                        print('curl -X POST http://localhost:8000/auth/login \\')
                        print('  -H "Content-Type: application/json" \\')
                        print('  -d \'{"email": "' + agent['email'] + '", "password": "Agent123!"}\'')
                
                for user in users:
                    if not user.get('existed'):
                        print(f"\n# Se connecter en tant que {user['full_name']}:")
                        print('curl -X POST http://localhost:8000/auth/login \\')
                        print('  -H "Content-Type: application/json" \\')
                        print('  -d \'{"email": "' + user['email'] + '", "password": "User123!"}\'')
            
            print("\n" + "=" * 80)
            print("✅ SCRIPT TERMINÉ AVEC SUCCÈS!")
            print("=" * 80)
            print()
            
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())