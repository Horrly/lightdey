"""Add a starter list of well-known neighbourhoods so the search isn't empty on day one.

Only area names are seeded — never reports. Everything shown about power
supply comes from real people. Safe to run on every deploy.
"""

from django.core.management.base import BaseCommand

from power.models import Area

STARTER_AREAS = {
    ("Lagos", "Lagos"): [
        "Yaba", "Surulere", "Ikeja", "Lekki", "Ajah", "Ikorodu", "Festac", "Gbagada", "Maryland",
        "Ogba", "Egbeda", "Ikotun", "Magodo", "Victoria Island", "Ikoyi", "Mushin", "Oshodi", "Ojota",
        "Ketu", "Isolo", "Ejigbo", "Agege", "Alimosho", "Apapa", "Ojo", "Sangotedo", "Akoka",
    ],
    ("Abuja", "FCT"): [
        "Wuse", "Garki", "Maitama", "Asokoro", "Gwarinpa", "Kubwa", "Lugbe", "Jabi", "Utako", "Lokogoma",
        "Karu", "Nyanya", "Life Camp", "Apo",
    ],
    ("Ibadan", "Oyo"): ["Bodija", "Challenge", "Dugbe", "Mokola", "Agodi", "Ring Road", "Akobo", "Samonda", "Iwo Road", "Apete"],
    ("Ile-Ife", "Osun"): ["Mayfair", "Lagere", "Asherifa", "Parakin", "OAU Campus"],
    ("Port Harcourt", "Rivers"): ["GRA Phase 2", "Rumuokoro", "Rumuola", "Trans Amadi", "Choba", "Woji", "Eliozu", "D-Line"],
    ("Benin City", "Edo"): ["GRA", "Ugbowo", "Uselu", "Ekenwan", "Sapele Road"],
    ("Enugu", "Enugu"): ["Independence Layout", "New Haven", "Trans Ekulu", "Abakpa", "Uwani"],
    ("Kano", "Kano"): ["Nassarawa GRA", "Sabon Gari", "Tarauni", "Gyadi-Gyadi"],
    ("Abeokuta", "Ogun"): ["Panseke", "Oke-Ilewo", "Ibara", "Kuto"],
    ("Ilorin", "Kwara"): ["Tanke", "GRA", "Fate", "Taiwo"],
    ("Osogbo", "Osun"): ["Oke-Fia", "Ogo Oluwa", "Alekuwodo"],
}


class Command(BaseCommand):
    help = "Create starter neighbourhoods (names only, no reports)."

    def handle(self, *args, **options):
        created = 0
        for (city, state), names in STARTER_AREAS.items():
            for name in names:
                if not Area.objects.filter(name__iexact=name, city__iexact=city).exists():
                    Area.objects.create(name=name, city=city, state=state)
                    created += 1
        self.stdout.write(f"Seeded {created} new area(s); {Area.objects.count()} total.")
