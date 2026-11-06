"""api"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from downstream import heartbeat, register, sender

app = FastAPI(title="LarkBot", redirect_slashes=False)


class RegisterReq(BaseModel):
    program: str
    base_url: str
    cmd: str
    path: str


class HeartbeatReq(BaseModel):
    program: str


class SendTextReq(BaseModel):
    program: str
    target: str
    content: str


class SendFileReq(BaseModel):
    program: str
    target: str
    file_name: str
    content_base64: str
    duration_ms: int | None = None


def ok(code=0, message="ok", data=None):
    return {"code": code, "message": message, "data": data}


def fail(http_status, code, message, headers=None):
    return JSONResponse(status_code=http_status,
                        content={"code": code, "message": message, "data": None},
                        headers=headers)


@app.exception_handler(RequestValidationError)
async def _validation_error(request: Request, exc: RequestValidationError):
    summary = "; ".join(
        f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in exc.errors()
    )
    return fail(400, 4007, f"请求参数不合法: {summary}")


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    return fail(exc.status_code, 0, str(exc.detail), exc.headers)


@app.exception_handler(Exception)
async def _unhandled_error(request: Request, exc: Exception):
    return fail(500, 5000, "Internal Server Error")


@app.post("/register")
def _register(req: RegisterReq):
    try:
        data = register.register(req.program, req.base_url, req.cmd, req.path)
    except ValueError as e:
        return fail(400, 4007, str(e))
    if data["overwritten"]:
        return ok(1001, "注册成功（覆盖）", {"program_id": data["program_id"]})
    return ok(0, "ok", {"program_id": data["program_id"]})


@app.post("/heartbeat")
def _heartbeat(req: HeartbeatReq):
    if heartbeat.beat(req.program):
        return ok()
    return fail(404, 0, f"程序未注册: {req.program}")


@app.post("/send/text")
def _send_text(req: SendTextReq):
    return _submit_result(sender.submit_text(req.program, req.target, req.content))


@app.post("/send/file")
def _send_file(req: SendFileReq):
    return _submit_result(sender.submit_file(req.program, req.target, req.file_name,
                                             req.content_base64, req.duration_ms))


def _submit_result(res):
    if res.code == 0:
        return ok(res.code, res.message, res.data)
    return fail(res.http_status, res.code, res.message)


@app.get("/health")
def _health():
    return ok()
