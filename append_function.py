"""
Append analyze_security_risk function to intelligence.py
"""

function_code = '''

def analyze_security_risk(mentions: List[Dict[str, Any]], vip_name: str) -> List[Dict[str, Any]]:
    """
    Analyze mentions for security risks using Gemini.
    
    Args:
        mentions: List of mentions (from web/social media)
        vip_name: Name of the VIP being protected
        
    Returns:
        List of analyzed threats with risk levels
    """
    if not mentions:
        return []
    
    if not GEMINI_KEYS:
        logger.warning("Skipping security analysis (no keys). Returning empty list.")
        return []
    
    try:
        # Get next API key in rotation
        api_key = get_next_api_key()
        genai.configure(api_key=api_key)
        logger.info(f"Using API key #{(_key_index % len(GEMINI_KEYS)) + 1} for security analysis")
        
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # Prepare mentions for analysis
        mentions_text = []
        for i, mention in enumerate(mentions):
            content = mention.get('content', '') or mention.get('snippet', '') or mention.get('title', '')
            source = mention.get('source', 'Unknown')
            mentions_text.append(f"{i+1}. [{source}] {content[:200]}")
        
        prompt = f"""
        You are an Executive Security Analyst protecting {vip_name}.
        Analyze these mentions and identify security threats:

        {chr(10).join(mentions_text)}

        For each mention, determine:
        1. **risk_level**: HIGH, MEDIUM, or LOW
        2. **threat_type**: IMPERSONATION, DOXXING, SMEAR, or GENERAL
        3. **reason**: Brief explanation of the threat
        4. **content**: The original content
        5. **source**: Where it came from

        Criteria:
        - **IMPERSONATION (HIGH)**: Someone pretending to be {vip_name}, fake accounts, scam links
        - **DOXXING (HIGH)**: Private info leaked (address, phone, family details)
        - **SMEAR (MEDIUM/HIGH)**: Coordinated negative campaign, false accusations
        - **GENERAL (LOW)**: Normal news, fan posts, neutral mentions

        Return ONLY a JSON array of threat objects, one for each mention:
        [
            {{
                "index": 1,
                "risk_level": "HIGH",
                "threat_type": "IMPERSONATION",
                "reason": "Fake account claiming to be {vip_name}",
                "content": "...",
                "source": "Twitter"
            }},
            ...
        ]
        """
        
        response = model.generate_content(prompt)
        
        # Clean up response text
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
        
        threats = json.loads(response_text)
        
        # Merge with original mention data
        analyzed_threats = []
        for threat in threats:
            idx = threat.get('index', 1) - 1
            if 0 <= idx < len(mentions):
                original = mentions[idx]
                analyzed_threats.append({
                    **original,
                    'risk_level': threat.get('risk_level', 'LOW'),
                    'threat_type': threat.get('threat_type', 'GENERAL'),
                    'reason': threat.get('reason', 'No specific threat detected'),
                    'analyzed': True
                })
        
        logger.info(f"Analyzed {len(analyzed_threats)} threats")
        return analyzed_threats
        
    except Exception as e:
        logger.error(f"Security analysis failed: {str(e)}")
        # Return mentions with default LOW risk
        return [
            {
                **mention,
                'risk_level': 'LOW',
                'threat_type': 'GENERAL',
                'reason': 'Analysis failed',
                'analyzed': False
            }
            for mention in mentions
        ]
'''

# Append to intelligence.py
with open('backend/services/intelligence.py', 'a', encoding='utf-8') as f:
    f.write(function_code)

print("✅ Added analyze_security_risk function to intelligence.py")
