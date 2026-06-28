import json, csv, datetime, sys

# ============================================================
# SIGNAL — Intent-Aware Candidate Ranker for Redrob Hackathon
# Team Apex01 | Poovarasu S & Ajai Kumar R
# Track 1: Intelligent Candidate Discovery
# ============================================================

# JD-derived constants
MUST_HAVE_SKILLS = {
    'embeddings','embedding','sentence-transformers','sentence transformer',
    'faiss','pinecone','weaviate','qdrant','milvus','opensearch','elasticsearch',
    'vector database','vector search','vector db','hybrid search',
    'retrieval','rag','reranking','reranker','ranking','search',
    'ndcg','mrr','map','evaluation','a/b test','a/b testing',
    'python','llm','fine-tuning','fine tuning','lora','qlora','peft',
    'xgboost','learning to rank','recommendation','recommendation system',
    'nlp','information retrieval','bm25','semantic search','dense retrieval',
    'transformer','bert','gpt','langchain','openai','e5','bge'
}
NICE_TO_HAVE = {'distributed systems','large-scale inference','open-source','open source','hr-tech','marketplace'}
SERVICES_DISQUALIFIERS = {'tcs','infosys','wipro','accenture','cognizant','capgemini','tech mahindra','hcl','ibm'}
PURE_RESEARCH_DISQUALIFIERS = {'research scientist','research engineer','research intern','phd student'}
WRONG_DOMAIN = {'computer vision','speech recognition','robotics','mechanical','civil','chemical','marketing manager','operations manager','customer support','sales','finance','accounting','hr manager'}

# Indian AI company founding dates for tenure validation
COMPANY_FOUNDING = {
    'krutrim': 2023, 'sarvam': 2023, 'sarvam ai': 2023,
    'zepto': 2021, 'blinkit': 2021, 'swiggy': 2014,
    'ola': 2010, 'nykaa': 2012, 'razorpay': 2014,
    'cred': 2018, 'meesho': 2015, 'moengage': 2014,
    'browserstack': 2011, 'freshworks': 2010,
}

def days_since(date_str):
    if not date_str: return 9999
    try:
        d = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
        return (datetime.datetime.now() - d).days
    except: return 9999

def score_skills(candidate):
    skills = candidate.get('skills', [])
    sigs = candidate.get('redrob_signals', {})
    
    skill_names_raw = {s['name'].lower() for s in skills}
    skill_score = 0.0
    matched = 0
    
    for s in skills:
        name = s['name'].lower()
        prof = s.get('proficiency','beginner')
        end = s.get('endorsements', 0)
        dur = s.get('duration_months', 0)
        
        # Check relevance
        is_must = any(k in name for k in MUST_HAVE_SKILLS)
        is_nice = any(k in name for k in NICE_TO_HAVE)
        
        if not (is_must or is_nice):
            continue
        
        matched += 1
        
        # Base weight
        w = 1.0 if is_must else 0.4
        
        # Proficiency multiplier
        prof_mult = {'expert': 1.2, 'advanced': 1.0, 'intermediate': 0.7, 'beginner': 0.35}.get(prof, 0.5)
        
        # Endorsement trust (don't trust "advanced" with 0 endorsements)
        if prof in ('expert','advanced') and end == 0:
            prof_mult *= 0.5  # halve suspicious high-proficiency zero-endorse
        
        # Duration signal
        dur_mult = min(1.2, 0.6 + (dur / 36) * 0.6) if dur > 0 else 0.5
        
        # Assessment score from redrob if available
        assess = sigs.get('skill_assessment_scores', {})
        assess_boost = 0
        for akey, ascore in assess.items():
            if any(k in akey.lower() for k in MUST_HAVE_SKILLS):
                assess_boost = max(assess_boost, ascore / 100 * 0.15)
        
        skill_score += w * prof_mult * dur_mult
    
    # Normalize: cap at ~8 matched skills worth
    skill_score = min(skill_score / 6.0, 1.0)
    
    # Assess bonus
    assess = sigs.get('skill_assessment_scores', {})
    assess_total = 0
    assess_n = 0
    for akey, ascore in assess.items():
        if any(k in akey.lower() for k in MUST_HAVE_SKILLS):
            assess_total += ascore
            assess_n += 1
    if assess_n > 0:
        skill_score = min(1.0, skill_score + (assess_total / assess_n / 100) * 0.1)
    
    return round(skill_score, 4)

def score_career(candidate):
    history = candidate.get('career_history', [])
    profile = candidate.get('profile', {})
    yoe = profile.get('years_of_experience', 0)
    current_title = profile.get('current_title','').lower()
    
    if not history: return 0.0
    
    # YOE fit: 5-9 ideal, 4-10 acceptable
    if 5 <= yoe <= 9:
        yoe_score = 1.0
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        yoe_score = 0.75
    elif 3 <= yoe < 4 or 11 < yoe <= 13:
        yoe_score = 0.45
    else:
        yoe_score = 0.15
    
    # Career trajectory: reward product company experience
    product_months = 0
    services_months = 0
    ai_relevant_months = 0
    total_months = 0
    
    for job in history:
        co = job.get('company','').lower()
        title = job.get('title','').lower()
        dur = job.get('duration_months', 0)
        desc = job.get('description','').lower()
        industry = job.get('industry','').lower()
        co_size = job.get('company_size','')
        total_months += dur
        
        # Services check
        is_services = any(s in co for s in SERVICES_DISQUALIFIERS) or 'it services' in industry
        if is_services:
            services_months += dur
        else:
            product_months += dur
        
        # AI-relevant check
        ai_keywords = {'retrieval','ranking','embedding','recommendation','nlp','search','ml','ai','lm','llm','vector','rerank'}
        if any(k in desc for k in ai_keywords) or any(k in title for k in ai_keywords):
            ai_relevant_months += dur
    
    services_ratio = services_months / max(total_months, 1)
    product_ratio = product_months / max(total_months, 1)
    ai_ratio = ai_relevant_months / max(total_months, 1)
    
    # Penalize pure services background hard
    if services_ratio > 0.85:
        career_base = 0.2
    elif services_ratio > 0.6:
        career_base = 0.45
    else:
        career_base = 0.7 + product_ratio * 0.2
    
    # Reward AI-relevant experience
    career_base = min(1.0, career_base + ai_ratio * 0.25)
    
    # Title coherence check (honeypot detection)
    wrong = any(w in current_title for w in WRONG_DOMAIN)
    if wrong:
        career_base *= 0.15  # severe penalty for title mismatch
    
    return round(career_base * yoe_score, 4)

def score_behavioral(candidate):
    sigs = candidate.get('redrob_signals', {})
    if not sigs: return 0.5
    
    score = 0.0
    
    # AVAILABILITY signals (40% weight)
    last_active = days_since(sigs.get('last_active_date'))
    if last_active <= 7: avail = 1.0
    elif last_active <= 30: avail = 0.85
    elif last_active <= 90: avail = 0.65
    elif last_active <= 180: avail = 0.40
    else: avail = 0.15
    
    response_rate = sigs.get('recruiter_response_rate', 0.0)
    open_work = 1.15 if sigs.get('open_to_work_flag') else 0.85
    
    # Avg response time penalty
    avg_resp = sigs.get('avg_response_time_hours', 999)
    resp_speed = 1.0 if avg_resp <= 24 else (0.8 if avg_resp <= 72 else 0.6)
    
    availability_score = (avail * 0.5 + response_rate * 0.35 + (1 - min(avg_resp/200,1)) * 0.15) * open_work
    
    # INTENT signals (35% weight)
    apps_30d = min(sigs.get('applications_submitted_30d', 0), 10) / 10
    views_30d = min(sigs.get('profile_views_received_30d', 0), 50) / 50
    saved_30d = min(sigs.get('saved_by_recruiters_30d', 0), 20) / 20
    search_30d = min(sigs.get('search_appearance_30d', 0), 300) / 300
    interview_rate = sigs.get('interview_completion_rate', 0.5)
    
    intent_score = (apps_30d * 0.3 + views_30d * 0.2 + saved_30d * 0.25 + search_30d * 0.15 + interview_rate * 0.1)
    
    # QUALITY signals (25% weight)
    completeness = sigs.get('profile_completeness_score', 50) / 100
    endorsements = min(sigs.get('endorsements_received', 0), 100) / 100
    connections = min(sigs.get('connection_count', 0), 1000) / 1000
    github = max(sigs.get('github_activity_score', 0), 0) / 100
    verified = (0.5 if sigs.get('verified_email') else 0) + (0.5 if sigs.get('verified_phone') else 0)
    linkedin = 0.2 if sigs.get('linkedin_connected') else 0
    offer_acc = sigs.get('offer_acceptance_rate', 0)
    if offer_acc == -1: offer_acc = 0.5  # no prior offers = neutral
    
    quality_score = (completeness * 0.25 + endorsements * 0.2 + connections * 0.1 + 
                     github * 0.2 + verified * 0.1 + linkedin * 0.05 + offer_acc * 0.1)
    
    behavioral = (availability_score * 0.40 + intent_score * 0.35 + quality_score * 0.25)
    
    # Notice period: penalize >90 days
    notice = sigs.get('notice_period_days', 60)
    if notice <= 30: behavioral *= 1.05
    elif notice > 90: behavioral *= 0.88
    
    # Willing to relocate bonus (JD: Pune/Noida-preferred)
    if sigs.get('willing_to_relocate'): behavioral *= 1.03
    
    return round(min(behavioral, 1.0), 4)

def score_education(candidate):
    edu_list = candidate.get('education', [])
    if not edu_list: return 0.3
    
    best = 0.0
    for edu in edu_list:
        tier = edu.get('tier','tier_4')
        field = edu.get('field_of_study','').lower()
        degree = edu.get('degree','').lower()
        
        tier_score = {'tier_1': 1.0, 'tier_2': 0.8, 'tier_3': 0.6, 'tier_4': 0.4, 'tier_5': 0.25}.get(tier, 0.3)
        
        # Relevant field bonus
        relevant_fields = {'computer science','information technology','artificial intelligence','machine learning','data science','electronics','electrical','software'}
        if any(r in field for r in relevant_fields):
            tier_score = min(1.0, tier_score * 1.15)
        
        # Degree level
        if any(d in degree for d in ['phd','ph.d','doctorate']): tier_score *= 1.0
        elif any(d in degree for d in ['m.tech','m.e.','mtech','m.s.','msc']): tier_score *= 1.0
        elif any(d in degree for d in ['b.tech','b.e.','btech']): tier_score *= 0.95
        
        best = max(best, tier_score)
    
    return round(best, 4)

def detect_honeypot(candidate):
    """Returns a penalty multiplier (1.0 = clean, 0.0 = eliminate)"""
    skills = candidate.get('skills', [])
    history = candidate.get('career_history', [])
    profile = candidate.get('profile', {})
    current_title = profile.get('current_title', '').lower()
    
    # Strong signal 1: Title is clearly wrong domain
    wrong_title = any(w in current_title for w in WRONG_DOMAIN)
    
    # Count AI skills
    ai_skill_count = sum(1 for s in skills if any(k in s['name'].lower() for k in MUST_HAVE_SKILLS))
    total_skills = len(skills)
    
    # Strong signal 2: Many AI skills + zero AI career proof
    has_ai_career = False
    for job in history:
        desc = (job.get('description','') + job.get('title','')).lower()
        if any(k in desc for k in {'retrieval','ranking','embedding','recommendation','nlp','search','llm','vector'}):
            has_ai_career = True
            break
    
    ai_skill_no_career = ai_skill_count >= 5 and not has_ai_career
    
    # Strong signal 3: Tenure impossibility
    impossible_tenure = False
    for job in history:
        co = job.get('company','').lower()
        dur = job.get('duration_months', 0)
        for company_name, founding_year in COMPANY_FOUNDING.items():
            if company_name in co:
                max_months = (2026 - founding_year) * 12
                if dur > max_months + 6:  # 6-month buffer
                    impossible_tenure = True
    
    # Scoring
    strong_signals = sum([wrong_title, ai_skill_no_career, impossible_tenure])
    
    # Soft signals
    high_skills_low_endorse = total_skills > 12 and candidate.get('redrob_signals', {}).get('endorsements_received', 0) < 5
    research_only = all('research' in job.get('title','').lower() for job in history) if history else False
    
    weak_signals = sum([high_skills_low_endorse, research_only])
    
    if strong_signals >= 1:
        # Graduated penalty based on severity
        if wrong_title and ai_skill_no_career:
            return 0.05  # near-eliminate
        elif wrong_title:
            return 0.10
        elif ai_skill_no_career and impossible_tenure:
            return 0.10
        elif impossible_tenure:
            return 0.25
        else:
            return 0.30
    elif weak_signals >= 2:
        return 0.65
    
    return 1.0

def compute_final_score(candidate):
    skill = score_skills(candidate)
    career = score_career(candidate)
    behavioral = score_behavioral(candidate)
    edu = score_education(candidate)
    honeypot_mult = detect_honeypot(candidate)
    
    # India + relocation check (JD prefers India/Pune/Noida)
    country = candidate['profile'].get('country','').lower()
    location = candidate['profile'].get('location','').lower()
    location_bonus = 1.0
    if country == 'india':
        location_bonus = 1.05
        if any(city in location for city in ['pune','noida','delhi','hyderabad','bangalore','mumbai','bengaluru']):
            location_bonus = 1.08
    
    # Weighted final score
    base = (
        skill   * 0.35 +
        career  * 0.35 +
        behavioral * 0.20 +
        edu     * 0.10
    )
    
    final = base * honeypot_mult * location_bonus
    return round(min(final, 1.0), 6), skill, career, behavioral, edu, honeypot_mult

def build_reasoning(candidate, skill, career, behavioral, edu, hp):
    p = candidate['profile']
    sigs = candidate.get('redrob_signals', {})
    title = p.get('current_title','?')
    yoe = p.get('years_of_experience', 0)
    company = p.get('current_company','?')
    location = p.get('location','?')
    rr = sigs.get('recruiter_response_rate', 0)
    last_active = days_since(sigs.get('last_active_date'))
    
    skills_top = [s['name'] for s in candidate.get('skills',[]) if any(k in s['name'].lower() for k in MUST_HAVE_SKILLS)][:3]
    skills_str = ', '.join(skills_top) if skills_top else 'limited relevant skills'
    
    active_str = f"{last_active}d ago" if last_active < 9999 else "unknown"
    hp_str = f" [FLAGGED: honeypot penalty {hp:.2f}x]" if hp < 0.5 else ""
    
    return (f"{title} at {company}, {yoe:.1f}yr YOE, {location}. "
            f"Top skills: {skills_str}. Response rate: {rr:.0%}, last active {active_str}. "
            f"Skill={skill:.3f} Career={career:.3f} Behavioral={behavioral:.3f} Edu={edu:.3f}{hp_str}")

def main():
    print("Loading and scoring 100K candidates...", file=sys.stderr)
    scored = []
    
    with open('/tmp/dataset/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl') as f:
        for i, line in enumerate(f):
            if i % 10000 == 0: print(f"  {i}...", file=sys.stderr)
            c = json.loads(line)
            score, sk, ca, beh, edu, hp = compute_final_score(c)
            scored.append((c['candidate_id'], score, sk, ca, beh, edu, hp, c))
    
    print("Ranking...", file=sys.stderr)
    scored.sort(key=lambda x: -x[1])
    top100 = scored[:100]
    
    # Write CSV
    outfile = '/tmp/Apex01.csv'
    with open(outfile, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['candidate_id','rank','score','reasoning'])
        for rank, (cid, score, sk, ca, beh, edu, hp, c) in enumerate(top100, 1):
            reasoning = build_reasoning(c, sk, ca, beh, edu, hp)
            writer.writerow([cid, rank, round(score,6), reasoning])
    
    print(f"\nDone! Written {outfile}", file=sys.stderr)
    print("\nTop 10 candidates:", file=sys.stderr)
    for rank, (cid, score, sk, ca, beh, edu, hp, c) in enumerate(top100[:10], 1):
        p = c['profile']
        print(f"  #{rank}: {p['current_title']} @ {p['current_company']} | YOE:{p['years_of_experience']} | Score:{score:.4f} | HP:{hp}", file=sys.stderr)

main()
