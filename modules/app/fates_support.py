from ..deps import *

router = APIRouter(
    tags = ["Support"],
    prefix = "/support/fates",
    include_in_schema = False
)

@router.get("/invite")
async def support(request: Request):
    return RedirectResponse(support_url)

@router.get("/request")
async def support(request: Request):
    return templates.TemplateResponse("request.html", {"request": request, "form": (await Form.from_formdata(request))})

# CREATE TABLE support_requests (
#    id uuid primary key DEFAULT uuid_generate_v4(),
#    enquiry_type text,
#    resolved boolean default false,
#    files bytea[],
#    title text,
#    description text,
#    bot_id BIGINT
#);

@router.post("/request")
@csrf_protect
async def support_post(request: Request, files: List[UploadFile] = File(None), enquiry_type: str = FForm("report_bot"), title: str = FForm("Untitled Request"), description: str = FForm("Untitled Request"), bot_id: int = FForm(0)):
    filenames = [f.filename for f in files]
    files = [bytes(f.file.read()) for f in files]
    id = uuid.uuid4()
    await db.execute("INSERT INTO support_requests (id, enquiry_type, resolved, files, filenames, title, description, bot_id) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", id, enquiry_type, False, files, filenames, title, description, bot_id)
    return HTMLResponse("<strong>Your Support Enquiry ID: " + str(id) + "</strong><br/><a href='/'>Go back home</a>")
