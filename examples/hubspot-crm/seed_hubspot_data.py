"""Seed HubSpot with realistic test data for the Mnemora demo.

Creates:
  - 15 companies (SaaS, fintech, healthcare, e-commerce, logistics)
  - 50 contacts (3-5 per company, mixed English/Spanish names)
  - 25 deals (various stages, $5K-$500K)
  - 20 tickets (mixed priorities, statuses, spread over 3 months)

All objects are associated: contact→company, deal→company, deal→contact,
ticket→contact.

Usage:
    python seed_hubspot_data.py           # create test data
    python seed_hubspot_data.py --clean   # delete seeded data
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress

console = Console()

HUBSPOT_API_BASE = "https://api.hubapi.com"
SEED_MANIFEST = Path(__file__).parent / ".seed_manifest.json"

# ---------------------------------------------------------------------------
# Companies (15)
# ---------------------------------------------------------------------------

COMPANIES: list[dict[str, str]] = [
    # --- US SaaS ---
    {"name": "Acme Corp", "industry": "COMPUTER_SOFTWARE", "annualrevenue": "2500000", "numberofemployees": "150", "website": "https://acmecorp.io", "description": "Developer productivity platform for CI/CD pipelines and cloud deployments.", "city": "San Francisco", "country": "United States"},
    {"name": "GlobalTech Industries", "industry": "INFORMATION_TECHNOLOGY_AND_SERVICES", "annualrevenue": "18000000", "numberofemployees": "420", "website": "https://globaltech.com", "description": "Enterprise IT consulting and managed cloud services for Fortune 500 companies.", "city": "New York", "country": "United States"},
    {"name": "CloudNine Analytics", "industry": "COMPUTER_SOFTWARE", "annualrevenue": "8500000", "numberofemployees": "95", "website": "https://cloudnine.ai", "description": "AI-powered business intelligence platform with real-time data pipelines.", "city": "Austin", "country": "United States"},
    # --- Fintech ---
    {"name": "NovaPay Financial", "industry": "FINANCIAL_SERVICES", "annualrevenue": "12000000", "numberofemployees": "200", "website": "https://novapay.com", "description": "Payment processing and embedded finance APIs for SaaS platforms.", "city": "Miami", "country": "United States"},
    {"name": "FinanzaPro", "industry": "FINANCIAL_SERVICES", "annualrevenue": "3200000", "numberofemployees": "65", "website": "https://finanzapro.com.py", "description": "Plataforma de pagos digitales y billetera electrónica para el mercado paraguayo.", "city": "Asunción", "country": "Paraguay"},
    # --- Healthcare ---
    {"name": "Pinnacle Health Systems", "industry": "HOSPITAL_HEALTH_CARE", "annualrevenue": "45000000", "numberofemployees": "500", "website": "https://pinnaclehealth.com", "description": "Hospital management software with EHR integration and telemedicine capabilities.", "city": "Boston", "country": "United States"},
    {"name": "MediTrack Brasil", "industry": "HOSPITAL_HEALTH_CARE", "annualrevenue": "6800000", "numberofemployees": "120", "website": "https://meditrack.com.br", "description": "Sistema de gestão hospitalar com prontuário eletrônico e agendamento inteligente.", "city": "São Paulo", "country": "Brazil"},
    # --- E-commerce ---
    {"name": "ShopFlow", "industry": "RETAIL", "annualrevenue": "15000000", "numberofemployees": "180", "website": "https://shopflow.io", "description": "Headless commerce platform with AI-driven product recommendations.", "city": "Seattle", "country": "United States"},
    {"name": "MercadoRápido", "industry": "RETAIL", "annualrevenue": "4500000", "numberofemployees": "85", "website": "https://mercadorapido.cl", "description": "Plataforma de marketplace para vendedores independientes en Chile y la región.", "city": "Santiago", "country": "Chile"},
    {"name": "TiendaMax", "industry": "RETAIL", "annualrevenue": "2800000", "numberofemployees": "55", "website": "https://tiendamax.com.ar", "description": "Solución de e-commerce todo-en-uno para PyMEs argentinas.", "city": "Buenos Aires", "country": "Argentina"},
    # --- Logistics ---
    {"name": "FleetOps Logistics", "industry": "LOGISTICS_AND_SUPPLY_CHAIN", "annualrevenue": "22000000", "numberofemployees": "310", "website": "https://fleetops.com", "description": "Real-time fleet management and route optimization for last-mile delivery.", "city": "Chicago", "country": "United States"},
    {"name": "CargoLink Colombia", "industry": "LOGISTICS_AND_SUPPLY_CHAIN", "annualrevenue": "5500000", "numberofemployees": "140", "website": "https://cargolink.co", "description": "Plataforma de logística y gestión de cadena de suministro para empresas colombianas.", "city": "Bogotá", "country": "Colombia"},
    # --- More SaaS ---
    {"name": "DataVault Security", "industry": "COMPUTER_SOFTWARE", "annualrevenue": "9200000", "numberofemployees": "110", "website": "https://datavault.security", "description": "Zero-trust data security platform with encryption-at-rest and RBAC.", "city": "Denver", "country": "United States"},
    {"name": "Nexus AI Labs", "industry": "COMPUTER_SOFTWARE", "annualrevenue": "950000", "numberofemployees": "18", "website": "https://nexusailabs.com", "description": "Early-stage AI agent orchestration startup building autonomous workflow engines.", "city": "San Francisco", "country": "United States"},
    {"name": "BrightEdge Education", "industry": "E_LEARNING", "annualrevenue": "3800000", "numberofemployees": "70", "website": "https://brightedge.edu", "description": "Online learning platform with adaptive curriculum and AI tutoring for K-12.", "city": "Portland", "country": "United States"},
]

# ---------------------------------------------------------------------------
# Contacts (50) — 3-5 per company, keyed by company name
# ---------------------------------------------------------------------------

CONTACTS: list[dict[str, str]] = [
    # Acme Corp (4)
    {"firstname": "John", "lastname": "Mitchell", "email": "john@acmecorp.io", "phone": "+1-415-555-0101", "company": "Acme Corp", "lifecyclestage": "customer", "jobtitle": "CEO"},
    {"firstname": "Sarah", "lastname": "Chen", "email": "sarah.chen@acmecorp.io", "phone": "+1-415-555-0102", "company": "Acme Corp", "lifecyclestage": "customer", "jobtitle": "CTO"},
    {"firstname": "Marcus", "lastname": "Rivera", "email": "marcus@acmecorp.io", "phone": "+1-415-555-0103", "company": "Acme Corp", "lifecyclestage": "customer", "jobtitle": "VP of Engineering"},
    {"firstname": "Priya", "lastname": "Sharma", "email": "priya@acmecorp.io", "phone": "+1-415-555-0104", "company": "Acme Corp", "lifecyclestage": "customer", "jobtitle": "Senior Developer"},

    # GlobalTech Industries (4)
    {"firstname": "Jane", "lastname": "Rodriguez", "email": "jane.rodriguez@globaltech.com", "phone": "+1-212-555-0201", "company": "GlobalTech Industries", "lifecyclestage": "opportunity", "jobtitle": "CTO"},
    {"firstname": "David", "lastname": "Park", "email": "david.park@globaltech.com", "phone": "+1-212-555-0202", "company": "GlobalTech Industries", "lifecyclestage": "opportunity", "jobtitle": "VP of Sales"},
    {"firstname": "Rachel", "lastname": "Nguyen", "email": "rachel@globaltech.com", "phone": "+1-212-555-0203", "company": "GlobalTech Industries", "lifecyclestage": "lead", "jobtitle": "Product Manager"},
    {"firstname": "Omar", "lastname": "Hassan", "email": "omar@globaltech.com", "phone": "+1-212-555-0204", "company": "GlobalTech Industries", "lifecyclestage": "lead", "jobtitle": "Solutions Architect"},

    # CloudNine Analytics (3)
    {"firstname": "Emily", "lastname": "Thompson", "email": "emily@cloudnine.ai", "phone": "+1-512-555-0301", "company": "CloudNine Analytics", "lifecyclestage": "marketingqualifiedlead", "jobtitle": "CEO"},
    {"firstname": "Alex", "lastname": "Kim", "email": "alex.kim@cloudnine.ai", "phone": "+1-512-555-0302", "company": "CloudNine Analytics", "lifecyclestage": "marketingqualifiedlead", "jobtitle": "Head of Data"},
    {"firstname": "Jordan", "lastname": "Williams", "email": "jordan@cloudnine.ai", "phone": "+1-512-555-0303", "company": "CloudNine Analytics", "lifecyclestage": "subscriber", "jobtitle": "ML Engineer"},

    # NovaPay Financial (4)
    {"firstname": "Lisa", "lastname": "Patel", "email": "lisa.patel@novapay.com", "phone": "+1-305-555-0401", "company": "NovaPay Financial", "lifecyclestage": "customer", "jobtitle": "CEO"},
    {"firstname": "Robert", "lastname": "Kim", "email": "robert.kim@novapay.com", "phone": "+1-305-555-0402", "company": "NovaPay Financial", "lifecyclestage": "customer", "jobtitle": "VP of Product"},
    {"firstname": "Diana", "lastname": "Costa", "email": "diana@novapay.com", "phone": "+1-305-555-0403", "company": "NovaPay Financial", "lifecyclestage": "lead", "jobtitle": "Senior Developer"},
    {"firstname": "James", "lastname": "O'Brien", "email": "james@novapay.com", "phone": "+1-305-555-0404", "company": "NovaPay Financial", "lifecyclestage": "customer", "jobtitle": "DevOps Lead"},

    # FinanzaPro (3)
    {"firstname": "Alejandro", "lastname": "Benítez", "email": "alejandro@finanzapro.com.py", "phone": "+595-21-555-0501", "company": "FinanzaPro", "lifecyclestage": "opportunity", "jobtitle": "CEO"},
    {"firstname": "María", "lastname": "González", "email": "maria.gonzalez@finanzapro.com.py", "phone": "+595-21-555-0502", "company": "FinanzaPro", "lifecyclestage": "opportunity", "jobtitle": "CTO"},
    {"firstname": "Diego", "lastname": "Ramírez", "email": "diego@finanzapro.com.py", "phone": "+595-21-555-0503", "company": "FinanzaPro", "lifecyclestage": "salesqualifiedlead", "jobtitle": "Product Manager"},

    # Pinnacle Health Systems (4)
    {"firstname": "Katherine", "lastname": "Wong", "email": "katherine.wong@pinnaclehealth.com", "phone": "+1-617-555-0601", "company": "Pinnacle Health Systems", "lifecyclestage": "opportunity", "jobtitle": "CIO"},
    {"firstname": "Michael", "lastname": "Okonkwo", "email": "michael.o@pinnaclehealth.com", "phone": "+1-617-555-0602", "company": "Pinnacle Health Systems", "lifecyclestage": "opportunity", "jobtitle": "VP of IT"},
    {"firstname": "Amanda", "lastname": "Foster", "email": "amanda@pinnaclehealth.com", "phone": "+1-617-555-0603", "company": "Pinnacle Health Systems", "lifecyclestage": "lead", "jobtitle": "Clinical Systems Manager"},
    {"firstname": "Brian", "lastname": "Davis", "email": "brian.davis@pinnaclehealth.com", "phone": "+1-617-555-0604", "company": "Pinnacle Health Systems", "lifecyclestage": "subscriber", "jobtitle": "Integration Developer"},

    # MediTrack Brasil (3)
    {"firstname": "Lucas", "lastname": "Ferreira", "email": "lucas@meditrack.com.br", "phone": "+55-11-555-0701", "company": "MediTrack Brasil", "lifecyclestage": "salesqualifiedlead", "jobtitle": "CEO"},
    {"firstname": "Camila", "lastname": "Santos", "email": "camila@meditrack.com.br", "phone": "+55-11-555-0702", "company": "MediTrack Brasil", "lifecyclestage": "salesqualifiedlead", "jobtitle": "CTO"},
    {"firstname": "Rafael", "lastname": "Oliveira", "email": "rafael@meditrack.com.br", "phone": "+55-11-555-0703", "company": "MediTrack Brasil", "lifecyclestage": "lead", "jobtitle": "Tech Lead"},

    # ShopFlow (4)
    {"firstname": "Megan", "lastname": "Taylor", "email": "megan@shopflow.io", "phone": "+1-206-555-0801", "company": "ShopFlow", "lifecyclestage": "customer", "jobtitle": "CEO"},
    {"firstname": "Chris", "lastname": "Anderson", "email": "chris@shopflow.io", "phone": "+1-206-555-0802", "company": "ShopFlow", "lifecyclestage": "customer", "jobtitle": "CTO"},
    {"firstname": "Sophie", "lastname": "Martin", "email": "sophie@shopflow.io", "phone": "+1-206-555-0803", "company": "ShopFlow", "lifecyclestage": "customer", "jobtitle": "VP of Sales"},
    {"firstname": "Daniel", "lastname": "Lee", "email": "daniel.lee@shopflow.io", "phone": "+1-206-555-0804", "company": "ShopFlow", "lifecyclestage": "customer", "jobtitle": "Platform Architect"},

    # MercadoRápido (3)
    {"firstname": "Sebastián", "lastname": "Muñoz", "email": "sebastian@mercadorapido.cl", "phone": "+56-2-555-0901", "company": "MercadoRápido", "lifecyclestage": "opportunity", "jobtitle": "CEO"},
    {"firstname": "Valentina", "lastname": "Lagos", "email": "valentina@mercadorapido.cl", "phone": "+56-2-555-0902", "company": "MercadoRápido", "lifecyclestage": "opportunity", "jobtitle": "Head of Engineering"},
    {"firstname": "Matías", "lastname": "Contreras", "email": "matias@mercadorapido.cl", "phone": "+56-2-555-0903", "company": "MercadoRápido", "lifecyclestage": "lead", "jobtitle": "Full-Stack Developer"},

    # TiendaMax (3)
    {"firstname": "Martín", "lastname": "Fernández", "email": "martin@tiendamax.com.ar", "phone": "+54-11-555-1001", "company": "TiendaMax", "lifecyclestage": "marketingqualifiedlead", "jobtitle": "CEO"},
    {"firstname": "Luciana", "lastname": "Gómez", "email": "luciana@tiendamax.com.ar", "phone": "+54-11-555-1002", "company": "TiendaMax", "lifecyclestage": "marketingqualifiedlead", "jobtitle": "CTO"},
    {"firstname": "Nicolás", "lastname": "Pereyra", "email": "nicolas@tiendamax.com.ar", "phone": "+54-11-555-1003", "company": "TiendaMax", "lifecyclestage": "subscriber", "jobtitle": "Developer"},

    # FleetOps Logistics (4)
    {"firstname": "Steven", "lastname": "Carter", "email": "steven@fleetops.com", "phone": "+1-312-555-1101", "company": "FleetOps Logistics", "lifecyclestage": "customer", "jobtitle": "CEO"},
    {"firstname": "Michelle", "lastname": "Robinson", "email": "michelle@fleetops.com", "phone": "+1-312-555-1102", "company": "FleetOps Logistics", "lifecyclestage": "customer", "jobtitle": "VP of Operations"},
    {"firstname": "Kevin", "lastname": "Zhang", "email": "kevin@fleetops.com", "phone": "+1-312-555-1103", "company": "FleetOps Logistics", "lifecyclestage": "customer", "jobtitle": "CTO"},
    {"firstname": "Tanya", "lastname": "Brooks", "email": "tanya@fleetops.com", "phone": "+1-312-555-1104", "company": "FleetOps Logistics", "lifecyclestage": "customer", "jobtitle": "Integration Manager"},

    # CargoLink Colombia (3)
    {"firstname": "Andrés", "lastname": "Herrera", "email": "andres@cargolink.co", "phone": "+57-1-555-1201", "company": "CargoLink Colombia", "lifecyclestage": "salesqualifiedlead", "jobtitle": "CEO"},
    {"firstname": "Catalina", "lastname": "Vargas", "email": "catalina@cargolink.co", "phone": "+57-1-555-1202", "company": "CargoLink Colombia", "lifecyclestage": "salesqualifiedlead", "jobtitle": "Head of Technology"},
    {"firstname": "Felipe", "lastname": "Morales", "email": "felipe@cargolink.co", "phone": "+57-1-555-1203", "company": "CargoLink Colombia", "lifecyclestage": "lead", "jobtitle": "Backend Developer"},

    # DataVault Security (3)
    {"firstname": "Ryan", "lastname": "Murphy", "email": "ryan@datavault.security", "phone": "+1-720-555-1301", "company": "DataVault Security", "lifecyclestage": "customer", "jobtitle": "CEO"},
    {"firstname": "Jennifer", "lastname": "Wu", "email": "jennifer@datavault.security", "phone": "+1-720-555-1302", "company": "DataVault Security", "lifecyclestage": "customer", "jobtitle": "CISO"},
    {"firstname": "Andrew", "lastname": "Patel", "email": "andrew@datavault.security", "phone": "+1-720-555-1303", "company": "DataVault Security", "lifecyclestage": "customer", "jobtitle": "Senior Security Engineer"},

    # Nexus AI Labs (3)
    {"firstname": "Sam", "lastname": "Nakamura", "email": "sam@nexusailabs.com", "phone": "+1-415-555-1401", "company": "Nexus AI Labs", "lifecyclestage": "lead", "jobtitle": "CEO & Co-founder"},
    {"firstname": "Aria", "lastname": "Johansson", "email": "aria@nexusailabs.com", "phone": "+1-415-555-1402", "company": "Nexus AI Labs", "lifecyclestage": "lead", "jobtitle": "CTO & Co-founder"},
    {"firstname": "Tomás", "lastname": "Herrera", "email": "tomas@nexusailabs.com", "phone": "+1-415-555-1403", "company": "Nexus AI Labs", "lifecyclestage": "subscriber", "jobtitle": "AI Engineer"},

    # BrightEdge Education (3)
    {"firstname": "Laura", "lastname": "Simmons", "email": "laura@brightedge.edu", "phone": "+1-503-555-1501", "company": "BrightEdge Education", "lifecyclestage": "marketingqualifiedlead", "jobtitle": "CEO"},
    {"firstname": "Derek", "lastname": "Huang", "email": "derek@brightedge.edu", "phone": "+1-503-555-1502", "company": "BrightEdge Education", "lifecyclestage": "marketingqualifiedlead", "jobtitle": "VP of Product"},
    {"firstname": "Natalie", "lastname": "García", "email": "natalie@brightedge.edu", "phone": "+1-503-555-1503", "company": "BrightEdge Education", "lifecyclestage": "subscriber", "jobtitle": "Curriculum Designer"},
]

# ---------------------------------------------------------------------------
# Deals (25) — reference company name + primary contact index
# ---------------------------------------------------------------------------

DEALS: list[dict[str, Any]] = [
    # Acme Corp
    {"dealname": "Acme Corp - Enterprise Upgrade", "amount": "48000", "dealstage": "contractsent", "pipeline": "default", "closedate": "2026-03-30", "_company": "Acme Corp", "_contact_idx": 0},
    {"dealname": "Acme Corp - API Add-on Module", "amount": "12000", "dealstage": "qualifiedtobuy", "pipeline": "default", "closedate": "2026-04-15", "_company": "Acme Corp", "_contact_idx": 1},
    # GlobalTech
    {"dealname": "GlobalTech - Platform Migration", "amount": "195000", "dealstage": "presentationscheduled", "pipeline": "default", "closedate": "2026-05-01", "_company": "GlobalTech Industries", "_contact_idx": 4},
    {"dealname": "GlobalTech - Training & Enablement", "amount": "35000", "dealstage": "appointmentscheduled", "pipeline": "default", "closedate": "2026-04-10", "_company": "GlobalTech Industries", "_contact_idx": 5},
    # CloudNine
    {"dealname": "CloudNine - Data Pipeline Integration", "amount": "67000", "dealstage": "qualifiedtobuy", "pipeline": "default", "closedate": "2026-06-15", "_company": "CloudNine Analytics", "_contact_idx": 8},
    {"dealname": "CloudNine - POC Engagement", "amount": "8500", "dealstage": "appointmentscheduled", "pipeline": "default", "closedate": "2026-04-01", "_company": "CloudNine Analytics", "_contact_idx": 9},
    # NovaPay
    {"dealname": "NovaPay - Annual Renewal", "amount": "42000", "dealstage": "closedwon", "pipeline": "default", "closedate": "2026-02-28", "_company": "NovaPay Financial", "_contact_idx": 11},
    {"dealname": "NovaPay - Payment Gateway Integration", "amount": "85000", "dealstage": "decisionmakerboughtin", "pipeline": "default", "closedate": "2026-03-25", "_company": "NovaPay Financial", "_contact_idx": 12},
    # FinanzaPro
    {"dealname": "FinanzaPro - Memory API for Fraud Detection", "amount": "28000", "dealstage": "presentationscheduled", "pipeline": "default", "closedate": "2026-05-20", "_company": "FinanzaPro", "_contact_idx": 15},
    # Pinnacle Health
    {"dealname": "Pinnacle Health - HIPAA Compliance Suite", "amount": "320000", "dealstage": "qualifiedtobuy", "pipeline": "default", "closedate": "2026-07-01", "_company": "Pinnacle Health Systems", "_contact_idx": 18},
    {"dealname": "Pinnacle Health - EHR Memory Layer", "amount": "145000", "dealstage": "presentationscheduled", "pipeline": "default", "closedate": "2026-06-01", "_company": "Pinnacle Health Systems", "_contact_idx": 19},
    # MediTrack
    {"dealname": "MediTrack - Patient History Search", "amount": "52000", "dealstage": "appointmentscheduled", "pipeline": "default", "closedate": "2026-08-15", "_company": "MediTrack Brasil", "_contact_idx": 22},
    # ShopFlow
    {"dealname": "ShopFlow - Recommendation Engine Memory", "amount": "110000", "dealstage": "contractsent", "pipeline": "default", "closedate": "2026-03-20", "_company": "ShopFlow", "_contact_idx": 25},
    {"dealname": "ShopFlow - Scale Tier Upgrade", "amount": "24000", "dealstage": "closedwon", "pipeline": "default", "closedate": "2026-01-15", "_company": "ShopFlow", "_contact_idx": 26},
    # MercadoRápido
    {"dealname": "MercadoRápido - Seller Analytics Memory", "amount": "38000", "dealstage": "qualifiedtobuy", "pipeline": "default", "closedate": "2026-05-30", "_company": "MercadoRápido", "_contact_idx": 29},
    # TiendaMax
    {"dealname": "TiendaMax - E-commerce Agent POC", "amount": "15000", "dealstage": "appointmentscheduled", "pipeline": "default", "closedate": "2026-06-10", "_company": "TiendaMax", "_contact_idx": 32},
    # FleetOps
    {"dealname": "FleetOps - Route Optimization Memory", "amount": "175000", "dealstage": "decisionmakerboughtin", "pipeline": "default", "closedate": "2026-04-30", "_company": "FleetOps Logistics", "_contact_idx": 35},
    {"dealname": "FleetOps - Driver Behavior Analytics", "amount": "65000", "dealstage": "closedwon", "pipeline": "default", "closedate": "2026-02-10", "_company": "FleetOps Logistics", "_contact_idx": 36},
    # CargoLink
    {"dealname": "CargoLink - Supply Chain Memory Layer", "amount": "45000", "dealstage": "presentationscheduled", "pipeline": "default", "closedate": "2026-05-15", "_company": "CargoLink Colombia", "_contact_idx": 39},
    # DataVault
    {"dealname": "DataVault - Threat Intelligence Memory", "amount": "92000", "dealstage": "contractsent", "pipeline": "default", "closedate": "2026-04-05", "_company": "DataVault Security", "_contact_idx": 42},
    {"dealname": "DataVault - SOC Automation Add-on", "amount": "33000", "dealstage": "qualifiedtobuy", "pipeline": "default", "closedate": "2026-05-10", "_company": "DataVault Security", "_contact_idx": 43},
    # Nexus AI Labs
    {"dealname": "Nexus AI - Startup Pro Plan", "amount": "5800", "dealstage": "closedwon", "pipeline": "default", "closedate": "2026-01-20", "_company": "Nexus AI Labs", "_contact_idx": 45},
    {"dealname": "Nexus AI - Agent Orchestration Pilot", "amount": "18000", "dealstage": "decisionmakerboughtin", "pipeline": "default", "closedate": "2026-04-15", "_company": "Nexus AI Labs", "_contact_idx": 46},
    # BrightEdge
    {"dealname": "BrightEdge - Adaptive Learning Memory", "amount": "72000", "dealstage": "qualifiedtobuy", "pipeline": "default", "closedate": "2026-07-30", "_company": "BrightEdge Education", "_contact_idx": 48},
    # Acme Corp (closed lost)
    {"dealname": "Acme Corp - Legacy Migration (Abandoned)", "amount": "250000", "dealstage": "closedlost", "pipeline": "default", "closedate": "2025-11-15", "_company": "Acme Corp", "_contact_idx": 2},
]

# ---------------------------------------------------------------------------
# Tickets (20) — reference contact index
# ---------------------------------------------------------------------------

TICKETS: list[dict[str, Any]] = [
    # HIGH priority
    {"subject": "API rate limiting 429 errors in production", "content": "We're getting 429 errors when making batch calls to the semantic search endpoint. Started Monday after our deployment. Affects our recommendation engine — customers seeing stale results. Need urgent fix.", "hs_pipeline_stage": "2", "hs_ticket_priority": "HIGH", "_contact_idx": 3, "createdate": "2026-03-05"},
    {"subject": "Data loss after failed migration", "content": "Ran a bulk import of 50K vectors last night and the job timed out at 80%. Now we're missing about 10K vectors and the remaining ones seem corrupted — similarity scores are way off.", "hs_pipeline_stage": "2", "hs_ticket_priority": "HIGH", "_contact_idx": 27, "createdate": "2026-03-03"},
    {"subject": "Billing: double-charged on February invoice", "content": "Our February invoice shows $99 but we should be on the Pro plan at $49/month. Looks like we were charged for both January and February in the same cycle. Invoice #INV-2026-0247.", "hs_pipeline_stage": "4", "hs_ticket_priority": "HIGH", "_contact_idx": 11, "createdate": "2026-03-01"},
    {"subject": "Production outage: connection timeouts to Aurora", "content": "All our semantic search queries are timing out since 2:30 AM UTC. Getting 'connection refused' errors. Our monitoring shows 100% failure rate. This is blocking our entire platform.", "hs_pipeline_stage": "1", "hs_ticket_priority": "HIGH", "_contact_idx": 37, "createdate": "2026-02-28"},
    # MEDIUM priority
    {"subject": "Cannot access dashboard after SSO configuration", "content": "Configured SAML SSO with Okta yesterday. Now when I try to log in through our SSO portal, I get redirected to a blank page. Regular email login still works but we need SSO for compliance.", "hs_pipeline_stage": "2", "hs_ticket_priority": "MEDIUM", "_contact_idx": 19, "createdate": "2026-03-04"},
    {"subject": "Webhook delivery failures for episodic events", "content": "About 30% of our webhook notifications for new episodes are failing with 502 errors. The retry mechanism kicks in but there's a 5-minute delay which breaks our real-time dashboard.", "hs_pipeline_stage": "2", "hs_ticket_priority": "MEDIUM", "_contact_idx": 14, "createdate": "2026-02-25"},
    {"subject": "SDK v0.1.2 incompatible with Python 3.13", "content": "After upgrading to Python 3.13, the MnemoraSync client throws 'RuntimeError: cannot be called from a running event loop'. This worked fine on 3.12. We need 3.13 for other dependencies.", "hs_pipeline_stage": "1", "hs_ticket_priority": "MEDIUM", "_contact_idx": 24, "createdate": "2026-02-20"},
    {"subject": "Slow vector search above 100K embeddings", "content": "Our semantic search latency went from ~200ms to ~2.5s after we crossed 100K stored vectors. We're on the Pro plan. Is this expected? Are there index tuning options?", "hs_pipeline_stage": "2", "hs_ticket_priority": "MEDIUM", "_contact_idx": 9, "createdate": "2026-02-15"},
    {"subject": "RBAC: cannot create read-only API keys", "content": "We want to give our analytics team read-only access to semantic search but the dashboard only lets us create full-access keys. Is there a way to scope permissions per key?", "hs_pipeline_stage": "1", "hs_ticket_priority": "MEDIUM", "_contact_idx": 43, "createdate": "2026-02-10"},
    {"subject": "Integration with Salesforce not syncing contacts", "content": "Set up the Salesforce connector last week but contacts aren't flowing through. Webhook logs show timeouts on the Salesforce side. Already whitelisted our IPs.", "hs_pipeline_stage": "2", "hs_ticket_priority": "MEDIUM", "_contact_idx": 5, "createdate": "2026-01-28"},
    {"subject": "Memory namespace collision between staging and prod", "content": "Our staging and production environments are using the same agent_id but different API keys. However, semantic search results from staging are leaking into production responses.", "hs_pipeline_stage": "3", "hs_ticket_priority": "MEDIUM", "_contact_idx": 36, "createdate": "2026-01-20"},
    # LOW priority
    {"subject": "Feature request: bulk data export for compliance audit", "content": "We need to export all stored memories (semantic + episodic) for our annual SOC 2 audit. Currently have to query page by page. Would love a bulk export endpoint or S3 dump.", "hs_pipeline_stage": "1", "hs_ticket_priority": "LOW", "_contact_idx": 42, "createdate": "2026-03-02"},
    {"subject": "Feature request: team sharing for memory namespaces", "content": "We'd like multiple agents to share a memory namespace so our support and sales bots can access the same customer context. Currently each agent has isolated memory.", "hs_pipeline_stage": "1", "hs_ticket_priority": "LOW", "_contact_idx": 25, "createdate": "2026-02-22"},
    {"subject": "Documentation: missing examples for episodic summarize", "content": "The /v1/memory/episodic/{agent_id}/summarize endpoint is documented in the API reference but there are no code examples in the SDK docs or the quickstart guide.", "hs_pipeline_stage": "1", "hs_ticket_priority": "LOW", "_contact_idx": 46, "createdate": "2026-02-18"},
    {"subject": "Feature request: GraphQL API alternative", "content": "We're a GraphQL shop and wrapping your REST API adds boilerplate. Any plans for a GraphQL endpoint? Would especially help with fetching related data in one call.", "hs_pipeline_stage": "1", "hs_ticket_priority": "LOW", "_contact_idx": 33, "createdate": "2026-02-12"},
    {"subject": "Question: best practices for embedding model selection", "content": "Currently using the default Titan embeddings. Would switching to Cohere multilingual improve search quality for our Spanish-language content? Is there a way to bring our own model?", "hs_pipeline_stage": "4", "hs_ticket_priority": "LOW", "_contact_idx": 30, "createdate": "2026-02-05"},
    {"subject": "Typo in error message: 'Unauthroized' instead of 'Unauthorized'", "content": "When I use an expired API key, the error response body says 'Unauthroized access'. Minor typo but looks unprofessional in our logs.", "hs_pipeline_stage": "4", "hs_ticket_priority": "LOW", "_contact_idx": 47, "createdate": "2026-01-25"},
    {"subject": "Feature request: TTL per memory type", "content": "We want episodic memories to expire after 90 days but keep semantic memories forever. Currently TTL is set at the agent level. Can we have per-type TTL configuration?", "hs_pipeline_stage": "1", "hs_ticket_priority": "LOW", "_contact_idx": 38, "createdate": "2026-01-15"},
    {"subject": "SDK: type hints incomplete for search_memory response", "content": "The SearchResult model is missing the 'namespace' field in the type hints. It's returned in the API response but mypy flags it as an error when accessed.", "hs_pipeline_stage": "4", "hs_ticket_priority": "LOW", "_contact_idx": 10, "createdate": "2026-01-10"},
    {"subject": "Suggestion: add OpenTelemetry trace propagation", "content": "We use Datadog for APM and would love if the SDK propagated W3C trace context headers so we can see Mnemora latency in our distributed traces.", "hs_pipeline_stage": "1", "hs_ticket_priority": "LOW", "_contact_idx": 44, "createdate": "2026-01-05"},
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def create_object(
    client: httpx.Client, object_type: str, properties: dict[str, str]
) -> str:
    """Create a single CRM object. Returns its HubSpot ID."""
    resp = client.post(
        f"/crm/v3/objects/{object_type}",
        json={"properties": properties},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def delete_object(client: httpx.Client, object_type: str, obj_id: str) -> None:
    """Delete a single CRM object."""
    resp = client.delete(f"/crm/v3/objects/{object_type}/{obj_id}")
    if resp.status_code not in (200, 204, 404):
        resp.raise_for_status()


def associate(
    client: httpx.Client,
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    association_type: str,
) -> None:
    """Create an association between two CRM objects.

    Uses the v4 associations API:
      PUT /crm/v4/objects/{from}/{fromId}/associations/{to}/{toId}
    """
    resp = client.put(
        f"/crm/v4/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}",
        json=[{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": _ASSOC_TYPE_IDS[association_type]}],
    )
    if resp.status_code not in (200, 201, 204):
        # Log but don't fail — associations are best-effort
        console.print(f"  [yellow]![/] Association {from_type}/{from_id} → {to_type}/{to_id} failed: {resp.status_code}")


# HubSpot-defined association type IDs
_ASSOC_TYPE_IDS: dict[str, int] = {
    "contact_to_company": 1,
    "company_to_contact": 2,
    "deal_to_contact": 3,
    "contact_to_deal": 4,
    "deal_to_company": 5,
    "company_to_deal": 6,
    "ticket_to_contact": 15,
    "contact_to_ticket": 16,
}


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed(client: httpx.Client) -> dict[str, list[str]]:
    """Create all test data in HubSpot with associations."""
    manifest: dict[str, list[str]] = {
        "companies": [],
        "contacts": [],
        "deals": [],
        "tickets": [],
    }

    # Map company name → HubSpot ID for association lookups
    company_id_map: dict[str, str] = {}
    # List of contact HubSpot IDs in insertion order (matches CONTACTS indices)
    contact_ids: list[str] = []

    with Progress(console=console) as progress:
        # --- Companies ---
        task = progress.add_task("[cyan]Creating companies...", total=len(COMPANIES))
        for company in COMPANIES:
            obj_id = create_object(client, "companies", company)
            manifest["companies"].append(obj_id)
            company_id_map[company["name"]] = obj_id
            progress.advance(task)
        console.print(f"  [green]{len(COMPANIES)} companies created[/]")

        # --- Contacts ---
        task = progress.add_task("[cyan]Creating contacts...", total=len(CONTACTS))
        for contact in CONTACTS:
            # Remove internal fields before sending to API
            props = {k: v for k, v in contact.items() if not k.startswith("_")}
            obj_id = create_object(client, "contacts", props)
            manifest["contacts"].append(obj_id)
            contact_ids.append(obj_id)
            progress.advance(task)
        console.print(f"  [green]{len(CONTACTS)} contacts created[/]")

        # --- Contact → Company associations ---
        task = progress.add_task("[cyan]Associating contacts → companies...", total=len(CONTACTS))
        for i, contact in enumerate(CONTACTS):
            company_name = contact["company"]
            company_id = company_id_map.get(company_name)
            if company_id:
                associate(client, "contacts", contact_ids[i], "companies", company_id, "contact_to_company")
            progress.advance(task)
        console.print(f"  [green]{len(CONTACTS)} contact→company associations[/]")

        # --- Deals ---
        task = progress.add_task("[cyan]Creating deals...", total=len(DEALS))
        deal_ids: list[str] = []
        for deal in DEALS:
            props = {k: str(v) for k, v in deal.items() if not k.startswith("_")}
            obj_id = create_object(client, "deals", props)
            manifest["deals"].append(obj_id)
            deal_ids.append(obj_id)
            progress.advance(task)
        console.print(f"  [green]{len(DEALS)} deals created[/]")

        # --- Deal → Company + Deal → Contact associations ---
        task = progress.add_task("[cyan]Associating deals...", total=len(DEALS))
        for i, deal in enumerate(DEALS):
            company_name = deal.get("_company", "")
            company_id = company_id_map.get(company_name)
            if company_id:
                associate(client, "deals", deal_ids[i], "companies", company_id, "deal_to_company")

            contact_idx = deal.get("_contact_idx")
            if contact_idx is not None and contact_idx < len(contact_ids):
                associate(client, "deals", deal_ids[i], "contacts", contact_ids[contact_idx], "deal_to_contact")
            progress.advance(task)
        console.print(f"  [green]{len(DEALS)} deal associations[/]")

        # --- Tickets ---
        task = progress.add_task("[cyan]Creating tickets...", total=len(TICKETS))
        ticket_ids: list[str] = []
        for ticket in TICKETS:
            props = {k: v for k, v in ticket.items() if not k.startswith("_")}
            obj_id = create_object(client, "tickets", props)
            manifest["tickets"].append(obj_id)
            ticket_ids.append(obj_id)
            progress.advance(task)
        console.print(f"  [green]{len(TICKETS)} tickets created[/]")

        # --- Ticket → Contact associations ---
        task = progress.add_task("[cyan]Associating tickets → contacts...", total=len(TICKETS))
        for i, ticket in enumerate(TICKETS):
            contact_idx = ticket.get("_contact_idx")
            if contact_idx is not None and contact_idx < len(contact_ids):
                associate(client, "tickets", ticket_ids[i], "contacts", contact_ids[contact_idx], "ticket_to_contact")
            progress.advance(task)
        console.print(f"  [green]{len(TICKETS)} ticket→contact associations[/]")

    # Save manifest for cleanup
    SEED_MANIFEST.write_text(json.dumps(manifest, indent=2))

    total = sum(len(v) for v in manifest.values())
    console.print(f"\n[bold green]Seed complete: {total} objects created in HubSpot[/]")
    console.print(f"[dim]Manifest saved to {SEED_MANIFEST}[/]")
    return manifest


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

def clean(client: httpx.Client) -> None:
    """Delete all seeded data using the manifest.

    Deletes in reverse order (tickets → deals → contacts → companies)
    to avoid association conflicts.
    """
    if not SEED_MANIFEST.exists():
        console.print("[red]No seed manifest found (.seed_manifest.json). Nothing to clean.[/]")
        return

    manifest: dict[str, list[str]] = json.loads(SEED_MANIFEST.read_text())
    deletion_order = ["tickets", "deals", "contacts", "companies"]

    total = sum(len(manifest.get(t, [])) for t in deletion_order)
    deleted = 0

    with Progress(console=console) as progress:
        task = progress.add_task("[red]Cleaning seeded data...", total=total)
        for obj_type in deletion_order:
            ids = manifest.get(obj_type, [])
            for obj_id in ids:
                try:
                    delete_object(client, obj_type, obj_id)
                    deleted += 1
                except Exception as e:
                    console.print(f"  [yellow]![/] Failed to delete {obj_type}/{obj_id}: {e}")
                progress.advance(task)

    SEED_MANIFEST.unlink(missing_ok=True)
    console.print(f"\n[bold green]Cleanup complete: {deleted}/{total} objects deleted[/]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Seed HubSpot with test data")
    parser.add_argument("--clean", action="store_true", help="Delete seeded data")
    args = parser.parse_args()

    hubspot_token = os.environ.get("HUBSPOT_API_KEY", "")
    if not hubspot_token:
        console.print("[red]Missing HUBSPOT_API_KEY in .env[/]")
        sys.exit(1)

    client = httpx.Client(
        base_url=HUBSPOT_API_BASE,
        headers={"Authorization": f"Bearer {hubspot_token}"},
        timeout=30.0,
    )

    try:
        if args.clean:
            clean(client)
        else:
            seed(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
