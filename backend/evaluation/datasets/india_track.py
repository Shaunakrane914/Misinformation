"""
Aegis Protocol — India Multilingual Evaluation Track
===================================================
Curated gold evaluation benchmark for misinformation across Indian languages and contexts.

Languages covered:
- English (en-IN)
- Hindi (hi-IN)
- Marathi (mr-IN)
- Hinglish (hi-en)

Domains:
- Public Health & Medicine
- Monetary Policy & Banking / Finance
- Public Policy & Government Schemes
- Political Statements & Elections
- Infrastructure & Public Utilities

Annotation & Verification Protocol:
Every claim is grounded in primary institutional documents or accredited IFCN-signatory fact-checks
(e.g., Press Information Bureau Fact Check, Reserve Bank of India notifications, AltNews, BoomLive, THIP Media).
"""

from typing import Dict, List, Any


INDIA_GOLD_TRACK_ITEMS: List[Dict[str, Any]] = [
    # ── Health (English, Hindi, Marathi, Hinglish) ──
    {
        "claim_id": "IN-HLTH-001",
        "claim": "Consuming raw crushed garlic with warm water cures stage 4 cancer without chemotherapy.",
        "language": "English",
        "language_code": "en-IN",
        "domain": "Public Health",
        "label": 1,  # 1 = Fake / False
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "Tata Memorial Hospital and WHO Oncology guidelines confirm garlic contains organosulfur compounds with mild anti-inflammatory properties, but has zero clinical efficacy as a curative cancer therapy.",
            "American Cancer Society clinical review demonstrates dietary garlic does not reverse malignant neoplasms."
        ],
        "source_urls": [
            "https://www.who.int/news-room/fact-sheets/detail/cancer",
            "https://tmc.gov.in/index.php/en/patient-education"
        ],
        "verification_source": "Tata Memorial Centre / WHO Oncology Desk",
        "annotation_notes": "Viral WhatsApp forwarded audio claim attributed to anonymous Ayurvedic practitioner."
    },
    {
        "claim_id": "IN-HLTH-002",
        "claim": "फिटकरी और हल्दी के पानी से गरारे करने पर कोरोना वायरस फेफड़ों में जाने से पहले ही खत्म हो जाता है।",
        "language": "Hindi",
        "language_code": "hi-IN",
        "domain": "Public Health",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "Ministry of Ayush and PIB Fact Check clarified that saline or alum gargling soothes mucosal irritation but cannot neutralize intracellular SARS-CoV-2 viral replication.",
            "Indian Council of Medical Research (ICMR) clinical protocol confirms gargles do not prevent respiratory viral infection."
        ],
        "source_urls": [
            "https://factcheck.pib.gov.in",
            "https://www.icmr.gov.in/guidelines.html"
        ],
        "verification_source": "PIB Fact Check / ICMR",
        "annotation_notes": "Widely shared viral Hindi graphic claiming household cure for respiratory viral load."
    },
    {
        "claim_id": "IN-HLTH-003",
        "claim": "उकडलेले लिंबू पाणी आणि बेकिंग सोडा प्यायल्याने शरीरातील सर्व प्रकारचे विषाणू नष्ट होतात.",
        "language": "Marathi",
        "language_code": "mr-IN",
        "domain": "Public Health",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "जागतिक आरोग्य संघटना (WHO) आणि वैद्यकीय तज्ज्ञांनुसार लिंबू आणि बेकिंग सोड्याचे मिश्रण शरीरातील रक्ताची आम्लता किंवा विषाणूंचा प्रादुर्भाव रोखत नाही.",
            "महाराष्ट्र आरोग्य विज्ञान विद्यापीठ (MUHS) मार्गदर्शक तत्त्वानुसार बेकिंग सोड्याचा अतिवापर गॅस्ट्रिक समस्या निर्माण करू शकतो."
        ],
        "source_urls": [
            "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/myth-busters",
            "https://www.muhs.ac.in"
        ],
        "verification_source": "WHO Myth Busters / MUHS Nashik",
        "annotation_notes": "Viral Marathi audio clip claiming alkaline water destroys lipid viral coats."
    },
    {
        "claim_id": "IN-HLTH-004",
        "claim": "NITI Aayog ne confirm kiya hai ki Bharat Biotech ka Covaxin vaccine ICMR and WHO approved hai.",
        "language": "Hinglish",
        "language_code": "hi-en",
        "domain": "Public Health",
        "label": 0,  # 0 = Real / True
        "canonical_verdict": "True",
        "supporting_evidence": [
            "World Health Organization granted Emergency Use Listing (EUL) to Bharat Biotech's BBV152 (Covaxin) on November 3, 2021.",
            "Central Drugs Standard Control Organisation (CDSCO) and ICMR co-developed and approved Covaxin under national immunization guidelines."
        ],
        "contradicting_evidence": [],
        "source_urls": [
            "https://www.who.int/news/item/03-11-2021-who-issues-emergency-use-listing-for-covaxin",
            "https://cdsco.gov.in"
        ],
        "verification_source": "WHO Official Press Release / CDSCO Gazette",
        "annotation_notes": "Factual Hinglish query verifying international and national regulatory accreditation."
    },

    # ── Finance & Banking (English, Hindi, Marathi, Hinglish) ──
    {
        "claim_id": "IN-FIN-001",
        "claim": "Reserve Bank of India has ordered the immediate cancellation of ₹500 currency notes from next month.",
        "language": "English",
        "language_code": "en-IN",
        "domain": "Finance & Banking",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "RBI official press release explicitly refutes viral rumors regarding the demonetization of ₹500 Mahatma Gandhi (New) Series notes.",
            "PIB Fact Check confirmed the circular being circulated on social media is fake and forged."
        ],
        "source_urls": [
            "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx",
            "https://factcheck.pib.gov.in"
        ],
        "verification_source": "Reserve Bank of India Press Release / PIB Fact Check",
        "annotation_notes": "Repeated viral rumor circulating morphed notification with fake RBI letterhead."
    },
    {
        "claim_id": "IN-FIN-002",
        "claim": "भारतीय रिझर्व्ह बँकेने युनिफाइड पेमेंट्स इंटरफेस (UPI) व्यवहारांवर 18% जीएसटी लावण्याचा निर्णय घेतला आहे.",
        "language": "Marathi",
        "language_code": "mr-IN",
        "domain": "Finance & Banking",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "केंद्रीय अर्थमंत्रालयाने स्पष्ट केले आहे की सामान्य ग्राहकांसाठी UPI व्यवहारांवर कोणताही सेवा कर किंवा १८% जीएसटी आकारला जात नाही.",
            "NPCI (National Payments Corporation of India) परिपत्रकानुसार सामान्य व्यक्ती ते व्यक्ती (P2P) आणि व्यक्ती ते व्यापारी (P2M) व्यवहार पूर्णपणे विनामूल्य आहेत."
        ],
        "source_urls": [
            "https://pib.gov.in/PressReleasePage.aspx?PRID=1853483",
            "https://www.npci.org.in"
        ],
        "verification_source": "Ministry of Finance Press Note / NPCI Clarification",
        "annotation_notes": "Viral Marathi social media graphic alleging hidden surcharges on UPI payments."
    },
    {
        "claim_id": "IN-FIN-003",
        "claim": "RBI ne Monetary Policy Committee meeting me repo rate ko unchanged rakha hai at 6.5%.",
        "language": "Hinglish",
        "language_code": "hi-en",
        "domain": "Finance & Banking",
        "label": 0,
        "canonical_verdict": "True",
        "supporting_evidence": [
            "RBI Governor statement from MPC bi-monthly resolution confirms policy repo rate held steady at 6.50% across multiple reviews.",
            "Statutory resolution published under Section 45ZB of the Reserve Bank of India Act, 1934."
        ],
        "contradicting_evidence": [],
        "source_urls": [
            "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=58334"
        ],
        "verification_source": "RBI Monetary Policy Statement / Financial Gazette",
        "annotation_notes": "Real financial statement commonly summarized in colloquial Hinglish market updates."
    },
    {
        "claim_id": "IN-FIN-004",
        "claim": "प्रधानमंत्री मुद्रा योजना के तहत सरकार सभी बेरोजगार युवाओं को बिना किसी गारंटी के 10 लाख रुपये का मुफ्त नकद दे रही है।",
        "language": "Hindi",
        "language_code": "hi-IN",
        "domain": "Finance & Banking",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "मुद्रा योजना (PMMY) एक संस्थागत ऋण (Loan) योजना है, न कि मुफ्त नकद अनुदान (Free Cash Grant)। इसे बैंक सत्यापन और व्यावसायिक योजना के बाद वापस चुकाना होता है।",
            "पीआईबी फैक्ट चेक ने पुष्टि की है कि बिना आवेदन या व्यावसायिक उद्देश्य के मुफ्त पैसे देने का दावा फर्जी है।"
        ],
        "source_urls": [
            "https://www.mudra.org.in",
            "https://factcheck.pib.gov.in"
        ],
        "verification_source": "MUDRA Official Scheme Guidelines / PIB Fact Check",
        "annotation_notes": "Deceptive phishing scheme promising free bank account transfers upon registration fee."
    },

    # ── Government Policy & Public Utilities (English, Hindi, Marathi, Hinglish) ──
    {
        "claim_id": "IN-POL-001",
        "claim": "Indian Railways announced that senior citizen concession on train tickets has been permanently abolished for all categories.",
        "language": "English",
        "language_code": "en-IN",
        "domain": "Public Policy",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "Ministry of Railways maintains concessions for specific accredited categories including patients with cancer, thalassemia, and orthopedic conditions.",
            "Standing Committee reports to Lok Sabha note broad senior concession was suspended during COVID-19, but parliamentary reviews remain ongoing without permanent statutory abolition."
        ],
        "source_urls": [
            "https://indianrailways.gov.in",
            "https://sansad.in/ls"
        ],
        "verification_source": "Ministry of Railways Clarification / Lok Sabha Question Archive",
        "annotation_notes": "Oversimplified headline claiming blanket permanent abolition across all passenger concession categories."
    },
    {
        "claim_id": "IN-POL-002",
        "claim": "केंद्र सरकारने नवीन वीज कायद्यानुसार सर्व जुने डिजिटल वीज मीटर सक्तीने काढून प्रीपेड स्मार्ट मीटर बसवण्याचे आदेश दिले आहेत.",
        "language": "Marathi",
        "language_code": "mr-IN",
        "domain": "Public Utilities",
        "label": 0,
        "canonical_verdict": "True",
        "supporting_evidence": [
            "Ministry of Power issued national guidelines under Revamped Distribution Sector Scheme (RDSS) mandating transition to prepayment smart metering across state DISCOMs.",
            "MSEDCL (महावितरण) official consumer circular confirms phase-wise rollout of smart prepaid meters across Maharashtra."
        ],
        "contradicting_evidence": [],
        "source_urls": [
            "https://powermin.gov.in/en/content/revamped-distribution-sector-scheme",
            "https://www.mahadiscom.in"
        ],
        "verification_source": "Ministry of Power RDSS Gazette / MSEDCL Maharashtra Notification",
        "annotation_notes": "Factual regional reporting regarding central government power distribution modernization scheme."
    },
    {
        "claim_id": "IN-POL-003",
        "claim": "Supreme Court of India ruled that Aadhaar card is not mandatory for opening a savings bank account.",
        "language": "English",
        "language_code": "en-IN",
        "domain": "Public Policy",
        "label": 0,
        "canonical_verdict": "True",
        "supporting_evidence": [
            "Supreme Court 5-judge Constitution Bench judgment in Justice K.S. Puttaswamy (Retd.) v. Union of India (2018) struck down Section 57 of Aadhaar Act requiring mandatory Aadhaar linkage for bank accounts.",
            "RBI Master Direction on KYC confirms officially valid documents (Passport, Voter ID, Driving License) are legally acceptable alternatives to Aadhaar."
        ],
        "contradicting_evidence": [],
        "source_urls": [
            "https://main.sci.gov.in/supremecourt/2012/35071/35071_2012_Judgement_26-Sep-2018.pdf",
            "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566"
        ],
        "verification_source": "Supreme Court of India Constitution Bench Judgment / RBI KYC Master Direction",
        "annotation_notes": "Statutory legal precedent frequently subject to misinformation by local bank branch representatives."
    },
    {
        "claim_id": "IN-POL-004",
        "claim": "Ab se WhatsApp par messages bhejne par 3 red ticks ka matlab govt agency ne case register kar liya hai.",
        "language": "Hinglish",
        "language_code": "hi-en",
        "domain": "Viral Social Claims",
        "label": 1,
        "canonical_verdict": "False",
        "supporting_evidence": [],
        "contradicting_evidence": [
            "WhatsApp uses end-to-end encryption with standard one grey tick (sent), two grey ticks (delivered), and two blue ticks (read). There is no feature or protocol for 'red ticks'.",
            "PIB Fact Check and Ministry of Electronics and Information Technology (MeitY) debunked this recurrent viral hoax multiple times."
        ],
        "source_urls": [
            "https://faq.whatsapp.com/514488229871587",
            "https://factcheck.pib.gov.in"
        ],
        "verification_source": "WhatsApp Technical Documentation / PIB Fact Check",
        "annotation_notes": "Long-running viral social hoax originating in 2020 claiming government surveillance tick indicators on chat."
    },

    # ── Infrastructure & Corporate (English, Hindi, Marathi, Hinglish) ──
    {
        "claim_id": "IN-INFRA-001",
        "claim": "Atal Setu (Mumbai Trans Harbour Link) is India's longest sea bridge connecting Sewri in Mumbai to Chirle in Navi Mumbai.",
        "language": "English",
        "language_code": "en-IN",
        "domain": "Infrastructure",
        "label": 0,
        "canonical_verdict": "True",
        "supporting_evidence": [
            "Mumbai Metropolitan Region Development Authority (MMRDA) project specifications record the bridge length at 21.8 km (16.5 km over sea), inaugurating it as the longest sea bridge in India.",
            "Official gazette notification of commissioning on January 12, 2024."
        ],
        "contradicting_evidence": [],
        "source_urls": [
            "https://mmrda.maharashtra.gov.in",
            "https://pib.gov.in/PressReleasePage.aspx?PRID=1995475"
        ],
        "verification_source": "MMRDA Project Dossier / Government of Maharashtra Gazette",
        "annotation_notes": "Factual regional infrastructure statement."
    },
    {
        "claim_id": "IN-INFRA-002",
        "claim": "नवी मुंबई आंतरराष्ट्रीय विमानतळावर नुकतीच भारतीय हवाई दलाच्या सुखोई-३० विमानाची यशस्वी चाचणी लँडिंग झाली.",
        "language": "Marathi",
        "language_code": "mr-IN",
        "domain": "Infrastructure",
        "label": 0,
        "canonical_verdict": "True",
        "supporting_evidence": [
            "CIDCO आणि भारतीय हवाई दल (IAF) यांच्या संयुक्त विद्यमाने ११ ऑक्टोबर २०२४ रोजी सुखोई ३०-एमकेआय लढाऊ विमानाचे धावपट्टीवर यशस्वी चाचणी लँडिंग पार पडले.",
            "नागरी विमान वाहतूक मंत्रालय अधिकृत प्रसिद्धीपत्रक क्रमांक PRID:2064112."
        ],
        "contradicting_evidence": [],
        "source_urls": [
            "https://cidco.maharashtra.gov.in",
            "https://pib.gov.in/PressReleasePage.aspx?PRID=2064112"
        ],
        "verification_source": "CIDCO Official Press Release / Ministry of Civil Aviation",
        "annotation_notes": "Factual Marathi report confirming military test landing on newly built civil runway."
    }
]


def load_india_gold_track() -> List[Dict[str, Any]]:
    """Returns the curated gold evaluation set for the India Multilingual Track."""
    return list(INDIA_GOLD_TRACK_ITEMS)


class IndiaMultilingualTrack:
    """Evaluator and accessor for the India Multilingual Gold Benchmark."""

    GOLD_ITEMS = INDIA_GOLD_TRACK_ITEMS

    def __init__(self):
        self.claims = list(INDIA_GOLD_TRACK_ITEMS)

    def get_claims(self) -> List[Dict[str, Any]]:
        return self.claims

    def get_statistics(self) -> Dict[str, Any]:
        languages = {}
        domains = {}
        for c in self.claims:
            lang = c.get("language", "Unknown")
            languages[lang] = languages.get(lang, 0) + 1
            dom = c.get("domain", "Unknown")
            domains[dom] = domains.get(dom, 0) + 1
        return {
            "total_claims": len(self.claims),
            "languages": languages,
            "domains": domains,
        }

