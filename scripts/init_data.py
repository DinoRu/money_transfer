"""
Script combiné pour initialiser complètement la base de données
- Crée les utilisateurs (admin + 2 users)
- Seed les données (devises, pays, taux, partenaires, comptes, frais)
"""
import sys
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import AsyncSessionLocal


def run_user_creation(db: AsyncSession):
    """Exécute la création des utilisateurs"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "ÉTAPE 1: CRÉATION DES UTILISATEURS" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")
    
    from create_users import create_admin_user, create_test_users
    
    # Créer l'admin
    print("\n👑 Création du super admin...")
    admin = create_admin_user(db)
    
    # Créer les utilisateurs
    print("\n👥 Création des utilisateurs de test...")
    users = create_test_users(db)
    
    return admin, users


def run_data_seeding(db: AsyncSession):
    """Exécute le seed des données"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "ÉTAPE 2: SEED DES DONNÉES" + " " * 29 + "║")
    print("╚" + "=" * 68 + "╝")
    
    from seed_data import (
        create_currencies,
        create_countries,
        create_exchange_rates,
        create_payment_partners,
        create_payment_accounts,
        create_fees
    )
    
    # Créer les données
    currencies = create_currencies(db)
    countries = create_countries(db, currencies)
    rates = create_exchange_rates(db, currencies)
    partners = create_payment_partners(db, countries)
    accounts = create_payment_accounts(db, partners)
    fees = create_fees(db, countries)
    
    return {
        "currencies": currencies,
        "countries": countries,
        "rates": rates,
        "partners": partners,
        "accounts": accounts,
        "fees": fees
    }


def main():
    """Fonction principale"""
    
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 8 + "INITIALISATION COMPLÈTE DE LA BASE DE DONNÉES" + " " * 14 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Initialiser la base de données
    print("\n🔧 Initialisation de la base de données...")
 
    print("✓ Base de données prête")
    
    # Créer une session
    db = AsyncSessionLocal()
    
    try:
        # Étape 1: Créer les utilisateurs
        admin, users = run_user_creation(db)
        
        # Étape 2: Seed les données
        data = run_data_seeding(db)
        
        # Résumé final
        print("\n" + "=" * 70)
        print("🎉 INITIALISATION COMPLÈTE TERMINÉE!")
        print("=" * 70)
        
        print("\n👥 UTILISATEURS:")
        print(f"   ✓ Admin: {admin['email'] if admin else 'Erreur'}")
        print(f"   ✓ Users: {len(users)} utilisateurs")
        
        print("\n📦 DONNÉES:")
        print(f"   ✓ Devises: {len(data['currencies'])}")
        print(f"   ✓ Pays: {len(data['countries'])}")
        print(f"   ✓ Taux de change: {len(data['rates'])}")
        print(f"   ✓ Partenaires: {len(data['partners'])}")
        print(f"   ✓ Comptes: {len(data['accounts'])}")
        print(f"   ✓ Frais: {len(data['fees'])}")
        
        # Informations de connexion
        print("\n" + "=" * 70)
        print("🔑 CONNEXION ADMIN")
        print("=" * 70)
        if admin and not admin.get('existed'):
            print(f"\nEmail: {admin['email']}")
            print(f"Mot de passe: {admin.get('password')}")
            print("\n# Commande curl:")
            print('curl -X POST http://localhost:8000/auth/login \\')
            print('  -H "Content-Type: application/json" \\')
            print('  -d \'{"email": "' + admin['email'] + '", "password": "' + admin.get('password', '') + '"}\'')
        
        # Exemples d'API
        print("\n" + "=" * 70)
        print("🧪 TESTER L'API")
        print("=" * 70)
        print("\n1. Démarrer l'API:")
        print("   python main_complete.py")
        
        print("\n2. Documentation interactive:")
        print("   http://localhost:8000/docs")
        
        print("\n3. Exemples de requêtes:")
        print("   • GET /api/v1/currencies - Lister les devises")
        print("   • GET /api/v1/countries - Lister les pays")
        print("   • GET /api/v1/payment-partners - Lister les partenaires")
        print("   • POST /api/v1/fees/calculate - Calculer des frais")
        
        print("\n" + "=" * 70)
        print()
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()