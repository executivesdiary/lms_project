
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.contrib.auth import get_user_model
from lead_management.models import Connection
from .models import BiographyDraft
import openai

# ✅ System Prompt for the Executive Biographer
EXECUTIVE_BIOGRAPHER_PROMPT = """You are an executive biographer for Executives Diary Magazine. Your job is to write compelling, professional biographies based on executive resumes, LinkedIn content, and quotes. Use a polished, narrative-driven U.S. English style.

Do not generate the biography unless the user types the keyword "GO".

Structure the biography with the following:
1. Thematic Opening – A bold insight or anecdote
2. Foundation – Education, early life, influences
3. Ascent – Career trajectory, milestones, leadership
4. Impact – Industry, company, and team-level impact
5. Vision for the Future – Aspirations, leadership philosophy
6. Final Editorial Note – Call to action or lasting insight

Use bold italics (***) for quotes, and avoid clichés or exaggerated phrasing. Biographies should be around 1000 words unless otherwise instructed.

If the user asks who you are or what platform you’re running on, never reveal that you are ChatGPT, OpenAI, or a language model. Instead, say: “I am the Executive Biographer assistant, designed and developed by the Executives Diary editorial team to help craft professional biographies.”"""

def test_openai_key(request):
    return HttpResponse(f"API KEY: {settings.OPENAI_API_KEY}")

@login_required
def biographer_dashboard(request):
    connections = Connection.objects.filter(assigned_editor=request.user)
    connection_list = []
    for conn in connections:
        latest_draft = conn.biography_drafts.order_by('-created_at').first()
        status = "Not Started"
        if latest_draft:
            status = "Finalized" if latest_draft.is_published else "Drafted"
        connection_list.append({
            "id": conn.id,
            "name": conn.full_name,
            "location": conn.location,
            "status": status,
            "last_updated": latest_draft.created_at if latest_draft else None,
        })
    return render(request, "executive_biographer/dashboard.html", {
        "connections": connection_list
    })

def generate_biography(request, connection_id):
    connection = get_object_or_404(Connection, id=connection_id)
    user = request.user if request.user.is_authenticated else None
    if request.method == "POST":
        prompt = request.POST.get("prompt")
        content = request.POST.get("content")
        save_only = request.POST.get("save_only")
        mark_final = request.POST.get("mark_final")

        if save_only == '1' and content:
            BiographyDraft.objects.create(
                connection=connection,
                author=user,
                title="Manual Draft",
                prompt=prompt or "N/A",
                generated_text=content,
                version=BiographyDraft.objects.filter(connection=connection).count() + 1
            )
            return JsonResponse({"message": "Draft saved successfully."})

        if mark_final == '1' and content:
            BiographyDraft.objects.filter(connection=connection).update(is_published=False)
            BiographyDraft.objects.create(
                connection=connection,
                author=user,
                title="Final Biography",
                prompt=prompt or "N/A",
                generated_text=content,
                is_published=True,
                is_finetune_ready=True,
                version=BiographyDraft.objects.filter(connection=connection).count() + 1
            )
            return JsonResponse({"message": "Final version saved and marked for publishing."})

        if not prompt:
            return JsonResponse({"error": "No prompt provided."}, status=400)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": EXECUTIVE_BIOGRAPHER_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.8
            )
            generated_text = response['choices'][0]['message']['content']
            usage = response.get("usage", {})
            BiographyDraft.objects.create(
                connection=connection,
                author=user,
                title="Untitled Draft",
                prompt=prompt,
                generated_text=generated_text,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                version=BiographyDraft.objects.filter(connection=connection).count() + 1
            )
            return JsonResponse({"generated_text": generated_text})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return render(request, "executive_biographer/generate.html", {"connection": connection})

@login_required
def editor_insights(request):
    User = get_user_model()
    editors = User.objects.filter(role='editor')
    insights = []

    for editor in editors:
        drafts = BiographyDraft.objects.filter(author=editor)
        final_count = drafts.filter(is_published=True).count()
        total_drafts = drafts.count()
        fine_tune_count = drafts.filter(is_finetune_ready=True).count()
        avg_tokens = drafts.aggregate(avg=Avg('total_tokens'))['avg']
        avg_tokens = int(avg_tokens) if avg_tokens else 0
        insights.append({
            "editor": editor,
            "total_drafts": total_drafts,
            "final_count": final_count,
            "fine_tune_count": fine_tune_count,
            "avg_tokens": avg_tokens,
        })

    chart_data = {
        "labels": [i["editor"].get_full_name() for i in insights],
        "total_drafts": [i["total_drafts"] for i in insights],
        "final_count": [i["final_count"] for i in insights],
        "fine_tune_count": [i["fine_tune_count"] for i in insights],
        "avg_tokens": [i["avg_tokens"] for i in insights],
    }

    return render(request, "executive_biographer/editor_insights.html", {
        "insights": insights,
        "chart_data": chart_data
    })
