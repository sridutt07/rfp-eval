"""Generate the four synthetic supplier RFP PDFs.

Each proposal responds to the same fictional procurement request
(RFP-2026-041, Metro Transit Authority) and is deliberately written with
different strengths, weaknesses, prices, schedules and evidence quality:

  Apex Systems    strong technical design + security; higher price; moderate schedule
  BrightPath Tech lowest price + fast timeline; weak compliance; limited experience
  NexaWorks       balanced; strongest implementation plan + support model
  Orbit Digital   strong experience + references; vague integration plan; medium pricing

Usage:
    python scripts/make_sample_pdfs.py [--out data/sample_pdfs]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RFP_TITLE = "RFP-2026-041 \u2014 Cloud-based Real-Time Passenger Information & Fleet Operations Platform"
BUYER = "Metro Transit Authority (MTA)"

# ---------------------------------------------------------------------------
# Proposal content. Blocks: ("h1", text) | ("p", text) | ("bullets", [...])
#                          | ("table", caption, headers, rows)
# ---------------------------------------------------------------------------

APEX = [
    ("h1", "1. Executive Summary"),
    ("p",
     "Apex Systems is pleased to respond to RFP-2026-041. With 12 years of experience delivering "
     "mission-critical transit technology across 40+ public-sector projects, we propose Apex TransitCloud, "
     "our proven real-time passenger information platform, tailored to the Metro Transit Authority\u2019s "
     "500-vehicle fleet. Our solution is engineered for precision: a cloud-native microservices architecture "
     "with true real-time vehicle tracking, an accessible passenger mobile app, 120 digital station signs, "
     "and a dispatch operations dashboard \u2014 all backed by enterprise-grade security."),
    ("p",
     "We offer a fixed price of $485,000 for full delivery and year-one support, with a 9-month implementation "
     "timeline from kickoff to final go-live. We acknowledge this is premium pricing relative to the market; "
     "it reflects our higher price point for certified security controls, redundant infrastructure, and senior "
     "engineering staff assigned full-time to your program."),
    ("h1", "2. Understanding of Requirements"),
    ("p",
     "MTA requires a single platform that unifies real-time bus location data, disseminates it to riders via "
     "mobile and station signage, and gives dispatchers a live operational picture. Key requirements include "
     "GTFS-RT open standards compliance, integration with the existing CAD/AVL and fare collection systems, "
     "99.9% platform uptime, WCAG 2.1 AA accessibility, and full go-live within 12 months. Our proposal "
     "addresses each requirement explicitly in the sections below."),
    ("h1", "3. Proposed Solution & Technical Approach"),
    ("p",
     "Apex TransitCloud is built on a cloud-native microservices architecture orchestrated with Kubernetes "
     "across multiple availability zones for full redundancy. Vehicle telemetry flows through an event-driven "
     "streaming pipeline (Apache Kafka) achieving sub-second real-time updates from bus to rider screen. The "
     "platform is horizontally scalable from 500 to over 2,000 vehicles without architectural changes."),
    ("p",
     "Integration is a core strength. We expose a versioned REST API plus webhooks, and our integration layer "
     "ships with pre-built connectors for major CAD/AVL suites; a dedicated integration workstream will map "
     "MTA\u2019s legacy interfaces during discovery. All data exchanges follow open standards (GTFS-RT, SIRI) "
     "so the Authority avoids vendor lock-in. Station signs run a resilient edge client that caches content "
     "locally and continues operating through network outages."),
    ("bullets", [
        "Microservices architecture on Kubernetes; independently deployable, independently scalable services.",
        "Event-driven real-time pipeline: median end-to-end latency under 2 seconds.",
        "Open API with versioned REST endpoints, webhooks, and GTFS-RT/SIRI feeds.",
        "Redundant multi-AZ deployment with automated failover and daily encrypted backups.",
    ]),
    ("h1", "4. Implementation Plan"),
    ("p",
     "Our 9-month timeline is organized into four phases with clear milestones, a full-time senior staffing "
     "plan, and a managed pilot before fleet-wide go-live. A named project manager and solution architect are "
     "assigned 100% for the program duration."),
    ("table", "Table 1 \u2014 Implementation milestones",
     ["Phase", "Duration", "Key milestones / deliverables"],
     [
         ["1. Discovery & Design", "6 weeks", "Requirements discovery sessions; CAD/AVL integration mapping; architecture sign-off"],
         ["2. Build & Integrate", "16 weeks", "Platform configuration; API integration; mobile app + signage build; milestone: system demo"],
         ["3. Pilot", "6 weeks", "50-bus pilot; dispatcher training; milestone: pilot acceptance"],
         ["4. Rollout & Go-live", "8 weeks", "Fleet-wide deployment; hypercare; milestone: final acceptance & go-live"],
     ]),
    ("p",
     "Staffing: 1 project manager, 1 solution architect, 4 senior engineers, 1 QA engineer, 1 UX specialist. "
     "Risks are managed through a joint risk register reviewed bi-weekly; our top mitigated risks are CAD/AVL "
     "interface delays (buffered in Phase 2) and signage hardware lead times (ordered at kickoff)."),
    ("h1", "5. Price Proposal"),
    ("p",
     "We propose a fixed price of $485,000. Our cost breakdown is fully transparent, and our assumptions are "
     "documented below so the Authority can evaluate total cost with confidence."),
    ("table", "Table 2 \u2014 Price breakdown (fixed price)",
     ["Item", "Amount (USD)"],
     [
         ["TransitCloud platform licenses (3 years)", "$180,000"],
         ["Implementation services", "$210,000"],
         ["Signage hardware integration (120 signs)", "$45,000"],
         ["Training & documentation", "$20,000"],
         ["Year-1 support & maintenance", "$30,000"],
         ["Total fixed price", "$485,000"],
     ]),
    ("bullets", [
        "Assumption: MTA provides CAD/AVL API access and test environment by week 3.",
        "Assumption: signage mounting and power are provided by MTA facilities.",
        "Assumption: up to 40 hours of stakeholder working sessions; excess billed at $195/hour.",
        "Payment terms: 20% kickoff, 40% at pilot acceptance, 40% at final go-live.",
    ]),
    ("h1", "6. Security, Compliance & Risk"),
    ("p",
     "Security is independently certified, not merely asserted. Apex Systems is ISO 27001 certified and "
     "completes a SOC 2 Type II audit annually; reports are available under NDA. All data is protected with "
     "AES-256 encryption at rest and TLS 1.3 in transit. We conduct annual third-party penetration tests and "
     "maintain a 30-day remediation SLA for critical findings."),
    ("p",
     "Access control follows least-privilege role-based access control with SSO/MFA integration to the "
     "Authority\u2019s identity provider. Our data privacy program aligns with GDPR and CCPA principles: rider "
     "data is minimized, anonymized for analytics, and never sold. Immutable audit logging supports full "
     "auditability of dispatcher actions and data exports."),
    ("h1", "7. Support Model, Experience & References"),
    ("p",
     "Apex provides a dedicated account manager, an 8x5 helpdesk with 4-hour response SLA, and 24/7 "
     "on-call coverage for severity-1 incidents. Our support model includes quarterly service reviews and "
     "proactive platform health monitoring."),
    ("p",
     "Relevant experience includes three similar projects: real-time fleet tracking for Harbor City Transit "
     "(600 vehicles, 2023), a passenger information rollout for Northline Rail (2024), and a dispatch "
     "modernization program for Capital Metro (2025). References available on request."),
]

BRIGHTPATH = [
    ("h1", "1. Executive Summary"),
    ("p",
     "BrightPath Tech is a fast-moving transit technology startup proposing BrightPath Live, a modern "
     "serverless passenger information platform for RFP-2026-041. We combine the lowest price in this "
     "competition with the fastest timeline: a fixed price of $312,000 and full go-live in 5 months. Our "
     "cloud-native serverless design keeps operating costs low and scales automatically with ridership demand."),
    ("p",
     "Founded three years ago, we have completed 6 transit and mobility projects. We are a young company and "
     "we are transparent about that: our proposal competes on speed, price, and modern engineering rather "
     "than decades of history."),
    ("h1", "2. Understanding of Requirements"),
    ("p",
     "MTA needs real-time bus tracking for 500 vehicles, a rider mobile app, 120 digital signs, a dispatcher "
     "dashboard, integration with CAD/AVL and fare systems, 99.9% uptime, accessibility compliance, and "
     "go-live within 12 months. BrightPath Live addresses each requirement with a streamlined, API-first "
     "approach."),
    ("h1", "3. Proposed Solution & Technical Approach"),
    ("p",
     "BrightPath Live is a serverless platform: vehicle positions stream in real time through "
     "managed event hubs into our prediction engine, which publishes GTFS-RT feeds consumed by the mobile app "
     "(React Native, iOS/Android), station signs, and the dispatcher dashboard. The architecture is "
     "sized automatically to demand, and every service exposes a documented API for integration with MTA\u2019s CAD/AVL "
     "environment."),
    ("bullets", [
        "Serverless real-time ingestion that grows automatically during peak service.",
        "API-first design: documented REST API for CAD/AVL integration and third-party developers.",
        "Cross-platform mobile app with trip planning, alerts, and accessibility features.",
        "Cloud-native deployment across two regions for resilience.",
    ]),
    ("h1", "4. Implementation Plan"),
    ("p",
     "Our aggressive 5-month timeline reflects a senior, co-located pod and a ruthless focus on milestones. "
     "Each phase ends with a formal milestone review and go/no-go decision."),
    ("table", "Table 1 \u2014 Implementation milestones",
     ["Phase", "Duration", "Key milestones / deliverables"],
     [
         ["1. Foundations", "6 weeks", "API mapping workshops; milestone: integration design sign-off"],
         ["2. Build", "10 weeks", "App, signs, dashboard build; milestone: feature-complete demo"],
         ["3. Pilot & Go-live", "6 weeks", "100-bus pilot; training; milestone: fleet-wide go-live"],
     ]),
    ("p",
     "Staffing: 1 delivery lead, 3 full-stack engineers, 1 mobile engineer, 1 QA engineer \u2014 all senior, "
     "all dedicated. A condensed pilot on 100 buses de-risks the transition, and our fixed-price model means "
     "schedule risk sits with us, not the Authority."),
    ("h1", "5. Price Proposal"),
    ("p",
     "Fixed price: $312,000. Our transparent pricing and detailed cost breakdown are below; this is a "
     "not-to-exceed commitment with all assumptions stated upfront."),
    ("table", "Table 2 \u2014 Price breakdown (fixed price, not-to-exceed)",
     ["Item", "Amount (USD)"],
     [
         ["Platform subscription (3 years, incl. hosting)", "$120,000"],
         ["Implementation services", "$140,000"],
         ["Signage software integration (120 signs)", "$28,000"],
         ["Training & documentation", "$12,000"],
         ["Year-1 support", "$12,000"],
         ["Total fixed price", "$312,000"],
     ]),
    ("bullets", [
        "Assumption: MTA provides CAD/AVL API documentation within 2 weeks of kickoff.",
        "Assumption: signage hardware is customer-provided; we deliver the software client.",
        "Payment terms: 30% kickoff, 30% at feature-complete milestone, 40% at go-live.",
    ]),
    ("h1", "6. Security, Compliance & Risk"),
    ("p",
     "BrightPath follows standard security practices: encryption of data in transit and at rest, role-based "
     "access control for the dispatcher dashboard, and regular dependency patching through our automated "
     "CI/CD pipeline."),
    ("p",
     "We are transparent about current limits: detailed certifications are not specified yet \u2014 we are "
     "pursuing SOC 2 Type I in 2027 \u2014 and independent audit reports are not specified at this time. "
     "Access control beyond standard role-based controls has limited detail in this proposal, and our data "
     "retention policy will be finalized jointly during discovery. We welcome a security review workshop as "
     "a first milestone."),
    ("h1", "7. Support Model, Experience & References"),
    ("p",
     "Support is provided via email and chat during business hours with next-business-day response targets; "
     "critical incidents page our on-call engineer. We are candid that we have limited experience relative "
     "to incumbents: three years in business and six completed projects, with few references in "
     "large-agency rail/bus operations. Our reference customer is Lakeside Shuttle (45 vehicles, 2025), "
     "available for a reference call."),
]

NEXA = [
    ("h1", "1. Executive Summary"),
    ("p",
     "NexaWorks proposes a dependable, low-risk delivery of RFP-2026-041 for a fixed price of $398,000 over "
     "a 7-month program. With 10 years of transit systems experience across 25 projects, our differentiator "
     "is execution discipline: the most detailed implementation plan in this competition and a white-glove "
     "support model that stays with the Authority long after go-live."),
    ("p",
     "Our NexaTransit Suite is a proven, API-first platform already operating at four mid-size agencies. We "
     "pair it with a 24/7 support organization, a named delivery team, and a milestone-gated plan that gives "
     "MTA full visibility and control from kickoff through hypercare."),
    ("h1", "2. Understanding of Requirements"),
    ("p",
     "MTA\u2019s objectives are clear: unify real-time fleet data, serve riders through app and signage, equip "
     "dispatchers with live operations insight, integrate CAD/AVL and fare systems using published interface standards, sustain "
     "99.9% uptime, meet accessibility obligations, and go live within 12 months. This proposal maps every "
     "requirement to a deliverable, an owner, and a milestone."),
    ("h1", "3. Proposed Solution & Technical Approach"),
    ("p",
     "NexaTransit Suite uses a modular microservices architecture deployed on a managed container platform. "
     "A real-time ingestion layer normalizes CAD/AVL feeds into GTFS-RT within seconds; the prediction engine "
     "is tunable per route. The design is scalable to 1,500 vehicles and every capability is exposed through "
     "a versioned open API with sandbox access for MTA developers."),
    ("bullets", [
        "Modular microservices architecture; deploy only what the Authority needs.",
        "Real-time GTFS-RT pipeline with per-route prediction tuning.",
        "API-first integration layer with pre-built adapters for leading CAD/AVL vendors.",
        "Scalable, elastic cloud deployment with automated backup and disaster recovery.",
    ]),
    ("h1", "4. Implementation Plan"),
    ("p",
     "Our implementation plan is milestone-gated across five phases of the master project plan, each with entry/exit criteria, a RACI "
     "staffing chart, and a living risk register. This is the strongest implementation plan we have ever "
     "submitted, and we stand behind every date."),
    ("table", "Table 1 \u2014 Implementation milestones",
     ["Phase", "Duration", "Key milestones / deliverables"],
     [
         ["1. Mobilize", "3 weeks", "Kickoff; RACI & risk register baselined; milestone: project charter sign-off"],
         ["2. Design", "5 weeks", "Integration blueprints; UX prototypes; milestone: design freeze"],
         ["3. Build & Integrate", "10 weeks", "Configuration + CAD/AVL integration; milestone: system test complete"],
         ["4. Pilot", "5 weeks", "75-bus pilot; dispatcher certification; milestone: pilot acceptance"],
         ["5. Deploy & Hypercare", "5 weeks", "Phased fleet cutover; 30-day hypercare; milestone: final go-live"],
     ]),
    ("p",
     "Staffing (RACI-published): 1 program manager, 1 technical architect, 3 integration engineers, 2 QA "
     "analysts, 1 change-management lead. Our risk plan names 14 risks with owners and mitigations; the top "
     "three are legacy interface latency (mitigated by an adapter buffer), sign-mount civil works (ordered "
     "week 1), and training adoption (train-the-trainer with measured proficiency gates). A two-week management "
     "buffer protects the go-live milestone."),
    ("h1", "5. Price Proposal"),
    ("p",
     "Fixed price: $398,000. We pride ourselves on transparent pricing: the cost breakdown below is complete, "
     "and every assumption that could move the number is listed."),
    ("table", "Table 2 \u2014 Price breakdown (fixed price)",
     ["Item", "Amount (USD)"],
     [
         ["NexaTransit Suite licenses (3 years)", "$150,000"],
         ["Implementation & integration services", "$165,000"],
         ["Signage software & integration (120 signs)", "$38,000"],
         ["Training, change management & docs", "$25,000"],
         ["Year-1 24/7 support", "$20,000"],
         ["Total fixed price", "$398,000"],
     ]),
    ("bullets", [
        "Assumption: CAD/AVL vendor cooperates on interface specs within 30 days.",
        "Assumption: MTA provides staging hardware access for the integration lab.",
        "Assumption: training covers up to 60 dispatchers across 4 cohorts.",
        "Payment terms: 15% kickoff, 25% design freeze, 30% pilot acceptance, 30% go-live.",
    ]),
    ("h1", "6. Security, Compliance & Risk"),
    ("p",
     "NexaWorks is ISO 27001 certified with annual surveillance audits. Data is encrypted with AES-256 at rest "
     "and TLS 1.3 in transit; access control is role-based with MFA enforced for all administrative users. We "
     "perform quarterly vulnerability scans and an annual third-party penetration test, with findings tracked "
     "to closure in a shared register."),
    ("p",
     "Our privacy controls support GDPR-style data minimization: rider identifiers are tokenized at ingestion "
     "and analytics datasets are anonymized. Comprehensive audit logging gives the Authority full auditability "
     "of system access and data exports."),
    ("h1", "7. Support Model, Experience & References"),
    ("p",
     "Our support model is the strongest in this competition: 24/7 staffed helpdesk, 99.9% uptime SLA with "
     "service credits, a named account manager, quarterly business reviews, and proactive monitoring with "
     "15-minute critical-incident response. Training includes e-learning, live cohorts, and a certification "
     "program for dispatchers."),
    ("p",
     "Our track record spans 10 years and 25 transit technology projects, including four agencies of similar "
     "size to MTA. Similar project experience includes real-time information systems for Valley Transit (420 "
     "vehicles), MetroWest Buses (380 vehicles), and Coastal Rapid (510 vehicles). We provide four references "
     "with contact details in Appendix A."),
]

ORBIT = [
    ("h1", "1. Executive Summary"),
    ("p",
     "Orbit Digital brings 15 years of experience and 60+ successful public-sector technology programs to "
     "RFP-2026-041. We propose Orbit JourneyView, our mature passenger information platform, delivered for a "
     "fixed price of $442,000 on an 8-month timeline. Agencies choose Orbit for one reason: we have done this "
     "before, many times, and our references will tell you so."),
    ("p",
     "Our proposal emphasizes proven delivery and deep operational experience. JourneyView is live today at "
     "nine transit agencies, and our team includes specialists who have run transit control rooms themselves."),
    ("h1", "2. Understanding of Requirements"),
    ("p",
     "MTA seeks a unified platform for real-time fleet visibility, rider communications via app and signage, "
     "dispatcher operations, integration with CAD/AVL and fare systems, high availability, accessibility, and "
     "delivery within 12 months. Orbit\u2019s response draws on directly comparable deployments to de-risk "
     "every element."),
    ("h1", "3. Proposed Solution & Technical Approach"),
    ("p",
     "Orbit JourneyView is a mature, field-hardened platform processing real-time feeds for over 3,000 "
     "vehicles daily across our client base. The system publishes GTFS-RT and powers mobile apps, signs, and "
     "control-room video walls from a single operational data core."),
    ("p",
     "On integration: our integration plan is described at a high level in this proposal. The specific "
     "approach for MTA\u2019s legacy CAD/AVL interfaces remains vague pending discovery workshops, and the "
     "data migration plan is unclear at this stage. Scalability has limited detail beyond our current client "
     "footprint. We propose to finalize these elements jointly in the first four weeks, supported by an open "
     "API that has served third-party developers for six years."),
    ("bullets", [
        "Mature platform: 3,000+ vehicles under management across nine agencies.",
        "Single operational data core feeding app, signage, and control room.",
        "Open API with six years of third-party developer support.",
    ]),
    ("h1", "4. Implementation Plan"),
    ("p",
     "Our 8-month program follows a proven four-stage rollout used in nine prior deployments, with milestones "
     "at each stage gate and a dedicated transition manager."),
    ("table", "Table 1 \u2014 Implementation milestones",
     ["Phase", "Duration", "Key milestones / deliverables"],
     [
         ["1. Discover", "6 weeks", "Workshops; milestone: requirements baseline"],
         ["2. Configure", "12 weeks", "Platform configuration; milestone: integrated demo"],
         ["3. Trial", "6 weeks", "Live trial operation; milestone: trial sign-off"],
         ["4. Launch", "8 weeks", "Full launch; milestone: operational handover"],
     ]),
    ("p",
     "Staffing: 1 transition manager, 1 solution lead, 3 consultants, 1 trainer. Our phased cutover approach "
     "has been refined across many go-lives; dispatcher training is delivered by former control-room staff."),
    ("h1", "5. Price Proposal"),
    ("p",
     "Fixed price: $442,000. While this is a higher price than some competitors, it includes our most senior "
     "delivery team and an extended 60-day hypercare period."),
    ("table", "Table 2 \u2014 Price breakdown (fixed price)",
     ["Item", "Amount (USD)"],
     [
         ["JourneyView platform licenses (3 years)", "$170,000"],
         ["Delivery & configuration services", "$175,000"],
         ["Signage integration (120 signs)", "$42,000"],
         ["Training & documentation", "$25,000"],
         ["Year-1 support & 60-day hypercare", "$30,000"],
         ["Total fixed price", "$442,000"],
     ]),
    ("bullets", [
        "Assumption: MTA legacy system documentation is made available at kickoff.",
        "Assumption: integration effort capped at 400 hours; excess at $210/hour.",
        "Payment terms: 25% kickoff, 25% at integrated demo, 50% at operational handover.",
    ]),
    ("h1", "6. Security, Compliance & Risk"),
    ("p",
     "Orbit Digital holds SOC 2 Type II certification, renewed annually. All rider and operational data is "
     "encrypted at rest (AES-256) and in transit (TLS 1.2+). Access control is role-based with MFA for "
     "privileged accounts, and we retain immutable audit logs for two years to support auditability."),
    ("p",
     "Our privacy framework minimizes personal data collection and our incident response plan is tested "
     "annually via tabletop exercises with client participation."),
    ("h1", "7. Support Model, Experience & References"),
    ("p",
     "Support is a signature strength: 24/7 staffed operations center, 99.95% uptime SLA, named account "
     "manager, and quarterly optimization reviews. Our support organization has earned a 96% satisfaction "
     "rating across our client base."),
    ("p",
     "Our track record is unmatched in this competition: 15 years in business, 60+ public-sector programs, "
     "and similar project experience at nine transit agencies including Grand Central Transit (700 vehicles), "
     "Bayline Metro (550 vehicles), and MetroSouth (480 vehicles). We enclose six references with direct "
     "contact details \u2014 more than any competitor \u2014 and invite the Authority to call every one of them."),
]


def _build_pdf(supplier: str, tagline: str, date: str, blocks, out_path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=26, spaceAfter=6)
    tagline_style = ParagraphStyle("Tagline", parent=styles["Normal"], fontSize=12,
                                   textColor=colors.HexColor("#444444"), spaceAfter=18)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceBefore=16, spaceAfter=8,
                        textColor=colors.HexColor("#1a3a5c"))
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.5, leading=15, spaceAfter=8,
                          alignment=4)
    bullet_style = ParagraphStyle("Bullet", parent=body, leftIndent=18, bulletIndent=8, spaceAfter=4)
    caption_style = ParagraphStyle("Caption", parent=styles["Normal"], fontSize=9,
                                   textColor=colors.HexColor("#555555"), spaceBefore=10, spaceAfter=4)
    cell = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9.5, leading=13)
    cell_header = ParagraphStyle("CellH", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(inch * 0.75, LETTER[1] - 0.55 * inch,
                          f"{supplier}  \u2014  Response to {RFP_TITLE.split(' \u2014')[0]}")
        canvas.drawRightString(LETTER[0] - inch * 0.75, 0.55 * inch, f"Page {doc.page}")
        canvas.drawString(inch * 0.75, 0.55 * inch, "CONFIDENTIAL \u2014 RFP Response")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.85 * inch, bottomMargin=0.85 * inch,
                            title=f"{supplier} \u2014 RFP Response", author=supplier)
    story = []
    story.append(Paragraph(supplier, title_style))
    story.append(Paragraph(tagline, tagline_style))
    story.append(Paragraph(f"Proposal in response to<br/>{RFP_TITLE}<br/>{BUYER}", body))
    story.append(Paragraph(f"Submission date: {date}", body))
    story.append(Spacer(1, 12))

    for block in blocks:
        kind = block[0]
        if kind == "h1":
            story.append(Paragraph(block[1], h1))
        elif kind == "p":
            story.append(Paragraph(block[1], body))
        elif kind == "bullets":
            items = [ListItem(Paragraph(b, bullet_style), leftIndent=18) for b in block[1]]
            story.append(ListFlowable(items, bulletType="bullet", start="\u2022"))
            story.append(Spacer(1, 6))
        elif kind == "table":
            _, caption, headers, rows = block
            data = [[Paragraph(h, cell_header) for h in headers]]
            data += [[Paragraph(str(x), cell) for x in row] for row in rows]
            widths = [3.6 * inch, 2.4 * inch] if len(headers) == 2 else [1.7 * inch, 1.2 * inch, 3.1 * inch]
            t = Table(data, colWidths=widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f9")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(Paragraph(caption, caption_style))
            story.append(t)
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 18))
    story.append(Paragraph("\u2014 End of proposal \u2014", caption_style))
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"Wrote {out_path} ({out_path.stat().st_size // 1024} KB)")


SUPPLIERS = [
    ("Apex Systems", "Precision engineering. Proven security.", "September 10, 2026", APEX,
     "Apex_Systems_RFP_Response.pdf"),
    ("BrightPath Tech", "Fast. Affordable. Modern.", "September 11, 2026", BRIGHTPATH,
     "BrightPath_Tech_RFP_Response.pdf"),
    ("NexaWorks", "The dependable delivery partner.", "September 12, 2026", NEXA,
     "NexaWorks_RFP_Response.pdf"),
    ("Orbit Digital", "Experience you can trust.", "September 13, 2026", ORBIT,
     "Orbit_Digital_RFP_Response.pdf"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic supplier RFP PDFs.")
    parser.add_argument("--out", default=None, help="Output directory")
    args = parser.parse_args()
    out_dir = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "data" / "sample_pdfs"
    out_dir.mkdir(parents=True, exist_ok=True)
    for supplier, tagline, date, blocks, filename in SUPPLIERS:
        _build_pdf(supplier, tagline, date, blocks, out_dir / filename)


if __name__ == "__main__":
    main()
