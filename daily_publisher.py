import os, json, glob, random, requests, shutil, sys
from dotenv import load_dotenv
from pathlib import Path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
try:
    from upload.upload_instagram import upload_to_instagram
    from upload.upload_threads import upload_to_threads
    from upload.upload_facebook import upload_to_facebook, upload_to_facebook_story
    from upload.upload_to_youtube import upload_to_youtube
except ImportError as e:
    print(f"Error importing upload modules: {e}")
    pass
PROCESSED_DIR = "Processed_Videos"
PUBLISHED_LOG = "published_videos.json"
def get_already_published():
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []
def get_repost_counts():
    published = get_already_published()
    counts = {}
    for entry in published:
        vname = entry.get("video_name", "")
        counts[vname] = counts.get(vname, 0) + 1
    return counts
def mark_as_published(video_name, metadata):
    published = get_already_published()
    published.append({"video_name": video_name, "metadata": metadata})
    with open(PUBLISHED_LOG, 'w', encoding='utf-8') as f:
        json.dump(published, f, indent=4)
def select_video(specific_video=None):
    published = [item["video_name"] for item in get_already_published()]
    all_videos = sorted(glob.glob(os.path.join(PROCESSED_DIR, "*.mp4")))
    if specific_video:
        if os.path.exists(specific_video): return specific_video, os.path.basename(specific_video)
        else: return None, None
    unpublished = [(v, os.path.basename(v)) for v in all_videos if os.path.basename(v) not in published]
    if unpublished: return unpublished[0]
    if all_videos:
        rc = get_repost_counts()
        weights = [max(1, 1000 // (3 ** min(rc.get(os.path.basename(v), 0), 6))) for v in all_videos]
        sel = random.choices(all_videos, weights=weights, k=1)[0]
        return sel, os.path.basename(sel)
    return None, None
def generate_caption():
    api_key = os.getenv("POLLINATIONS_API_KEY")
    model = os.getenv("AI_MODEL", "openai")
    fallback_titles = [
        "Trump and Putin's Funniest Moments Together",
        "When Trump and Putin Start Roasting Each Other It's Over",
        "The Most Hilarious Trump vs Putin Comedy Compilation",
        "Trump and Putin Just Had the Funniest Exchange Ever",
        "POV: Trump and Putin at a Comedy Show Together",
        "These Trump and Putin Moments Are Pure Comedy Gold",
        "When World Leaders Try to Be Funny - Trump & Putin",
        "The Unreleased Footage of Trump and Putin Roasting",
        "Trump and Putin's Secret Comedy Routine Exposed",
        "The Funniest Trump-Putin Interaction You'll Ever See"
    ]
    fallback_descriptions = [
        "When two of the most powerful leaders decide to have a comedy battle, you know it's legendary. This compilation captures the most hilarious moments between Trump and Putin - unexpected jokes, subtle roasts, perfectly timed one-liners. The chemistry between these two is unmatched, and the way they play off each other's energy is pure entertainment.",
        "You've never seen world leaders like this before. Trump and Putin in the same room is already entertainment, but when they start trading jokes and roasts, it becomes pure comedy magic. The most hilarious exchanges, unexpected punchlines, and moments where even translators can't keep a straight face. The best part? Neither is trying to be funny - which makes it funnier."
    ]
    if not api_key:
        return random.choice(fallback_titles), random.choice(fallback_descriptions)
    vibes = [
        "hilarious and surprising",
        "playful and competitive",
        "absurd and entertaining",
        "nostalgic and funny"
    ]
    chosen_vibe = random.choice(vibes)
    prompt = (
        f"Write a unique, long, captivating title and description for a short video "
        f"for Facebook page 'Dustyvibe Chuckles'. "
        f"Page posts funny conversations and roasts between Trump and Putin. "
        f"Speak as a political comedy fan laughing at these world leaders. Vibe: {chosen_vibe}. "
        f"Description 4-6 sentences, engaging. Include: Like if these two should start a comedy tour! Comment your favorite moment! Follow Dustyvibe Chuckles! "
        f"Hashtags: #trump #putin #comedy #funny #politics #humor #worldleaders #viral #trending #hilarious. "
        f'Return JSON: {{"title": "...", "description": "..."}}'
    )
    try:
        resp = requests.post("https://gen.pollinations.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.9, "seed": random.randint(1, 999999)},
            timeout=30)
        resp.raise_for_status()
        content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        content = content.replace("`json", "").replace("`", "").strip()
        result = json.loads(content)
        return result.get("title", random.choice(fallback_titles)), result.get("description", random.choice(fallback_descriptions))
    except: return random.choice(fallback_titles), random.choice(fallback_descriptions)
def main():
    print("=" * 60)
    print("DAILY AUTOMATION STARTING")
    print("=" * 60)
    specific_video = sys.argv[1] if len(sys.argv) > 1 else None
    video_path, video_name = select_video(specific_video)
    if not video_path:
        print("No new videos found. Exiting.")
        return
    print(f"Selected: {video_name}")
    title, description = generate_caption()
    print(f"Title: {title}")
    combined = f"{title}\n\n{description}"
    sf = {"instagram_reel": False, "instagram_story": False, "facebook_reel": False, "facebook_story": False, "threads": False, "youtube": False}
    try:
        r = upload_to_instagram(video_path, combined, is_story=False)
        if r and r.get('status') != 'skipped': sf["instagram_reel"] = True
    except: pass
    try:
        r = upload_to_instagram(video_path, combined, is_story=True)
        if r and r.get('status') != 'skipped': sf["instagram_story"] = True
    except: pass
    try:
        r = upload_to_facebook(video_path, description, title=title)
        if r and r.get('status') != 'skipped': sf["facebook_reel"] = True
    except: pass
    try:
        r = upload_to_facebook_story(video_path)
        if r and r.get('status') != 'skipped': sf["facebook_story"] = True
    except: pass
    try:
        r = upload_to_threads(video_path, combined)
        if r and r.get('status') != 'skipped': sf["threads"] = True
    except: pass
    try:
        upload_to_youtube(video_path, title, description, tags=["trump", "putin", "comedy", "funny", "politics", "humor", "worldleaders", "viral", "trending", "hilarious"])
        sf["youtube"] = True
    except: pass
    pl = get_already_published()
    recycled = any(i["video_name"] == video_name for i in pl)
    mark_as_published(video_name, {"title": title, "description": description, "success_flags": sf, "recycled": recycled})
    pd = "Published_Videos"
    if not os.path.exists(pd): os.makedirs(pd)
    try: shutil.move(video_path, os.path.join(pd, video_name))
    except: pass
    print("DAILY AUTOMATION COMPLETE")
if __name__ == "__main__":
    main()

