# Python 코드 컨벤션

> **적용 대상**: FastAPI + SQLAlchemy 기반 프로젝트  
> **목적**: Model 중심의 일관된 API 설계 및 코드 구조 유지  
> **아키텍처 패턴**: Domain-Driven Module (도메인 주도 모듈 설계)

---

## 1. Model 중심 아키텍처 (Domain-Driven Module)

### 기본 철학

이 프로젝트는 **Domain-Driven Module** 방식을 지향합니다:

- Model(도메인 모델)을 중심으로 파일과 모듈을 분리
- 각 도메인은 독립적인 모듈로 구성되어 응집도 높음
- 도메인 간 의존성을 최소화하여 유지보수성 향상

### 기본 원칙

- **1 Model = 1 Module = 1 Endpoint**
- 각 모듈은 **Controller + Service + DTO** 세트로 구성
- 모든 엔드포인트는 Model을 기준으로 생성
- 기본 CRUD 작업은 항상 정의
- 도메인 경계를 명확히 하여 **높은 응집도, 낮은 결합도** 유지

### 구조

```
src/
├── models/
│   └── user.py                    (Model - 도메인 모델)
├── user/                          (도메인 모듈)
│   ├── user_controller.py         (API 엔드포인트)
│   ├── user_service.py            (비즈니스 로직)
│   └── dto/                       (데이터 전송 객체)
│       ├── create_user_dto.py
│       ├── update_user_dto.py
│       └── get_user_dto.py
├── common/                        (공통 서비스)
│   ├── auth_token.py
│   ├── embedding_service.py
│   └── ...
└── database.py                    (DB 연결 설정)
```

### Domain-Driven Module의 장점

1. **명확한 책임 분리**: 각 도메인이 독립적으로 관리됨
2. **높은 응집도**: 관련된 기능이 한 모듈에 집중
3. **낮은 결합도**: 도메인 간 의존성 최소화
4. **확장성**: 새로운 도메인 추가가 용이
5. **유지보수성**: 특정 도메인 수정 시 영향 범위가 명확

---

## 2. 네이밍 규칙

### Model → Endpoint → 파일/클래스 매핑

```
Model: User (PascalCase)
  ↓
Endpoint: /user (kebab-case 또는 snake_case)
  ↓
Folder: user/ (snake_case)
  ↓
Class: UserService (PascalCase)
File: user_service.py (snake_case)
```

### 파일 네이밍 패턴

| 구분 | 패턴 | 예시 |
|------|------|------|
| **Model** | `{model_name}.py` | `user.py`, `company.py` |
| **Controller** | `{model_name}_controller.py` | `user_controller.py` |
| **Service** | `{model_name}_service.py` | `user_service.py` |
| **DTO** | `{action}_{model_name}_dto.py` | `create_user_dto.py` |

### DTO 네이밍 패턴

```
HTTP Method + Model Name + _dto.py

GET    /user          → get_user_dto.py
POST   /user          → create_user_dto.py
PATCH  /user/:id      → update_user_dto.py
DELETE /user/:id      → (DTO 불필요)
```

### Python 네이밍 컨벤션

| 구분 | 스타일 | 예시 |
|------|--------|------|
| **클래스명** | PascalCase | `UserService`, `CreateUserDto` |
| **함수/메서드** | snake_case | `find_all()`, `get_current_user()` |
| **변수** | snake_case | `user_service`, `company_id` |
| **상수** | UPPER_SNAKE_CASE | `DB_CONN_URL`, `MAX_RETRY` |
| **파일명** | snake_case | `user_service.py`, `auth_token.py` |

---

## 3. CRUD 엔드포인트

### 기본 CRUD 5종

모든 Model 기반 모듈은 다음 엔드포인트를 기본으로 제공:

```python
# 1. Create
POST   /user

# 2. Read (List)
GET    /user

# 3. Read (Single)
GET    /user/{id}

# 4. Update
PATCH  /user/{id}

# 5. Delete
DELETE /user/{id}
```

### 추가 엔드포인트

- 기본 CRUD 외에 추가 기능이 필요한 경우 자유롭게 정의
- 동일한 Model을 사용하되 다른 비즈니스 로직이 필요할 때

```python
# 예시: 추가 엔드포인트
POST   /user/login
GET    /user/summary
POST   /user/bulk-create
```

---

## 5. 클래스 vs 모듈 함수 선택 기준

### 기본 원칙

Python에서는 **"상태가 있으면 클래스, 없으면 모듈 함수"**가 원칙입니다.

| 상태 유무 | 선택 | 이유 |
|----------|------|------|
| **상태 있음** | 클래스 | 인스턴스별 데이터 캡슐화 필요 |
| **상태 없음** | 모듈 함수 | 불필요한 복잡성 제거, Pythonic |

### 상태가 있는 경우 → 클래스 사용

```python
# ✅ 좋음: 상태를 가지므로 클래스가 적합
class ChatV2Service:
    def __init__(self, dto, company, vector):
        self.dto = dto              # 상태 저장
        self.company = company      # 상태 저장
        self.score = None           # 메서드 간 공유
    
    def search(self):
        result = self._do_search()
        self.score = result.score   # 상태 변경
        return result
    
    def get_score(self):
        return self.score           # 상태 참조


# ✅ 좋음: 설정/연결 상태를 유지
class SlackService:
    def __init__(self):
        self.channel_name = None
        self.data = None
    
    def set_channel_name(self, name):
        self.channel_name = name
    
    def send(self):
        # self.channel_name 사용
        ...
```

### 상태가 없는 경우 → 모듈 함수 사용

```python
# ❌ 나쁨: self를 사용하지 않는 클래스
class EmbeddingService:
    def make_vector(self, input_data: str) -> list[float]:
        api_key = os.getenv("UPSTAGE_API_KEY")  # 매번 환경변수 조회
        # self를 전혀 사용하지 않음!
        ...
        return vector


# ✅ 좋음: 모듈 함수로 변환
# embedding_service.py
def make_vector(input_data: str, is_question: bool = False) -> list[float]:
    """질문을 벡터로 변환"""
    api_key = os.getenv("UPSTAGE_API_KEY")
    ...
    return vector


# 사용
from src.common.embedding_service import make_vector
vector = make_vector("질문입니다")
```

### 판단 기준 체크리스트

클래스를 만들기 전에 다음을 확인하세요:

| 질문 | Yes → 클래스 | No → 모듈 함수 |
|------|-------------|---------------|
| `self`에 데이터를 저장하나요? | ✅ | ❌ |
| 메서드 간에 상태를 공유하나요? | ✅ | ❌ |
| 인스턴스별로 다른 설정이 필요한가요? | ✅ | ❌ |
| 생성자에서 의미있는 초기화를 하나요? | ✅ | ❌ |

### 현재 프로젝트 적용 예시

| 서비스 | self 사용 | 권장 스타일 |
|--------|----------|------------|
| `ChatV2Service` | ✅ dto, company, score 등 | 클래스 유지 |
| `SlackService` | ✅ channel_name, data 등 | 클래스 유지 |
| `EmbeddingService` | ❌ | 모듈 함수로 전환 권장 |
| `CompanyService` | ❌ | 모듈 함수로 전환 권장 |
| `TiktokenService` | ❌ | 모듈 함수로 전환 권장 |

### Java/JavaScript vs Python 철학 차이

| Java/JavaScript | Python |
|----------------|--------|
| "모든 것은 클래스 안에" | "필요할 때만 클래스" |
| `StringUtils.isEmpty(str)` | `not string` |
| `Collections.sort(list)` | `sorted(list)` |
| 클래스 = 기본 단위 | 모듈 = 기본 단위 |

> **참고**: Python 표준 라이브러리도 대부분 모듈 함수입니다.
> - `os.path.join()`, `json.loads()`, `datetime.now()`

---

## 6. Controller 패턴

### Controller 원칙

1. **역할**: Orchestration 담당 - Service 메서드들을 조합하여 요청 처리
2. **비즈니스 로직**: Service에서 구현하고 Controller는 조합하는 역할 지향
3. **에러 처리**: Controller에서 try-except로 처리
4. **응답 형식**: JSONResponse 사용

### Controller 구조

```python
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from src.user.user_service import UserService
from src.user.dto.create_user_dto import CreateUserDto
from src.common.auth_token import AuthToken

router = APIRouter(prefix="/user", responses={404: {"description": "Not found"}})

user_service = UserService()
auth_token = AuthToken()


@router.post("")
def create(
    create_user_dto: CreateUserDto,
    current_user: User = Depends(auth_token.get_current_user),
):
    try:
        user = user_service.save(create_user_dto)
        return {
            "id": user.id,
            "user_id": user.user_id,
            "created_at": user.created_at,
        }
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)
```

### 좋은 예시 vs 나쁜 예시

```python
# ✅ 좋음: Controller는 Service 조합만
@router.post("")
def create(create_dto: CreateDto):
    try:
        user = user_service.save(create_dto)
        notification_service.send_welcome_email(user)
        return {"id": user.id, "user_id": user.user_id}
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)


# ❌ 나쁨: Controller에 비즈니스 로직 구현
@router.post("")
def create(create_dto: CreateDto):
    try:
        # 중복 체크 로직이 Controller에 있음
        session = Session()
        existing = session.query(User).filter(User.user_id == create_dto.user_id).first()
        if existing:
            raise Exception("중복")
        # 복잡한 계산 로직
        calculated_value = create_dto.amount * 0.1 + ...
        return session.execute(insert(User).values(...))
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)
```

---

## 7. Service 패턴

### Service 원칙

1. **역할**: 비즈니스 로직 구현의 주체
2. **세션 관리**: 메서드 내에서 Session 생성/종료 관리
3. **메서드 구성**:
   - 기본 CRUD 메서드 (`save`, `find_all`, `find`, `update`, `delete`)
   - 필요에 따라 별도 메서드 추가 가능
   - private 헬퍼 메서드로 코드 분리 가능 (`_` prefix)
4. **에러 처리**: `raise Exception()` 또는 구체적인 예외로 던지기

### Service 구조

```python
from src.database import Session
from src.models.user import User
from src.user.dto.create_user_dto import CreateUserDto
from sqlalchemy import insert


class UserService:
    def save(self, create_user_dto: CreateUserDto):
        session = Session()
        try:
            stmt = insert(User).values(
                company_id=create_user_dto.company_id,
                user_id=create_user_dto.user_id,
            )
            result = session.execute(stmt)
            key = result.inserted_primary_key[0]
            session.commit()
            return self.find(key)
        except BaseException as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def find(self, id: str):
        session = Session()
        try:
            return session.query(User).filter(User.id == id).first()
        except BaseException as e:
            raise e
        finally:
            session.close()

    def find_all(self, company_id: str = None):
        session = Session()
        try:
            query = session.query(User)
            if company_id is not None:
                query = query.filter(User.company_id == company_id)
            return query.all()
        except BaseException as e:
            raise e
        finally:
            session.close()

    def update(self, id: str, update_dto: UpdateUserDto):
        session = Session()
        try:
            user = session.query(User).filter(User.id == id).first()
            if user is None:
                return None
            if update_dto.user_id is not None:
                user.user_id = update_dto.user_id
            session.commit()
            session.refresh(user)
            return user
        except BaseException as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete(self, id: str):
        session = Session()
        try:
            user = session.query(User).filter(User.id == id).first()
            session.delete(user)
            session.commit()
            return {"message": "success"}
        except BaseException as e:
            session.rollback()
            raise e
        finally:
            session.close()
```

### 세션 관리 패턴

```python
# ✅ 좋음: try-except-finally로 세션 관리
def find(self, id: str):
    session = Session()
    try:
        return session.query(User).filter(User.id == id).first()
    except BaseException as e:
        raise e
    finally:
        session.close()


# ❌ 나쁨: 세션 종료 누락
def find(self, id: str):
    session = Session()
    return session.query(User).filter(User.id == id).first()
    # 세션이 종료되지 않음!
```

### Service 메서드 통합 원칙

여러 메서드가 중복되는지 판단하고, 통합 가능 여부를 결정하는 기준입니다.

| 상황 | 판단 | 이유 |
|------|------|------|
| 같은 작업 + where 조건만 다름 | ✅ 파라미터로 통합 | `find_by_company`, `find_by_type` → `find_all(company_id, type_id)` |
| 권한이 다름 | ❌ 분리 유지 | 관리자 전용 조회 vs 사용자 본인 데이터 조회 |
| 실행 전후 로직이 다름 | ❌ 분리 유지 | 활성 데이터 조회 vs 만료 데이터 조회 |
| 반환 형태가 다름 | ❌ 분리 유지 | 목록 조회 vs 통계/집계 조회 |

---

## 8. DTO 구성

### 기본 DTO 3종 세트

```python
# 1. CreateDTO - POST 요청용
from pydantic import BaseModel

class CreateUserDto(BaseModel):
    company_id: str
    user_id: str
    user_pw: str


# 2. UpdateDTO - PATCH 요청용
from typing import Optional
from pydantic import BaseModel

class UpdateUserDto(BaseModel):
    user_id: Optional[str] = None
    user_pw: Optional[str] = None


# 3. GetDTO - GET 쿼리 파라미터용
from typing import Optional
from pydantic import BaseModel

class GetUserDto(BaseModel):
    company_id: Optional[str] = None
    user_id: Optional[str] = None
    page: Optional[int] = None
    limit: Optional[int] = None
```

### DTO 필드 구성 원칙

| DTO 타입 | 필드 특성 | 설명 |
|----------|----------|------|
| **CreateDTO** | 필수 필드 위주 | 클라이언트가 보내야 하는 필드 |
| **UpdateDTO** | 모든 필드 Optional | 수정 가능한 필드만 포함 |
| **GetDTO** | 모든 필드 Optional | 필터링, 페이징, 정렬 조건 |

### Pydantic Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional


class CreateUserDto(BaseModel):
    company_id: str = Field(..., min_length=1, description="회사 ID")
    user_id: str = Field(..., min_length=3, max_length=50, description="사용자 ID")
    user_pw: str = Field(..., min_length=8, description="비밀번호")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if not v.isalnum():
            raise ValueError('user_id는 영문자와 숫자만 허용됩니다')
        return v


class UpdateUserDto(BaseModel):
    user_id: Optional[str] = Field(None, min_length=3, max_length=50)
    user_pw: Optional[str] = Field(None, min_length=8)
```

---

## 9. Model (Entity) 패턴

### Model 정의

```python
# src/models/user.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Uuid, primary_key=True, server_default=db.FetchedValue(), info='고유번호')
    company_id = db.Column(db.ForeignKey('company.id'), nullable=False, info='회사 고유번호(외래키)')
    user_id = db.Column(db.String(255), nullable=False, unique=True, info='아이디')
    user_pw = db.Column(db.Text, nullable=False, info='패스워드')
    created_at = db.Column(db.DateTime(True), server_default=db.FetchedValue(), info='등록일')
    updated_at = db.Column(db.DateTime(True), server_default=db.FetchedValue(), info='수정일')

    # Relationship
    company = db.relationship('Company', primaryjoin='User.company_id == Company.id', backref='users')
```

### Model 작성 원칙

1. **테이블명**: `__tablename__`으로 명시적 지정 (snake_case)
2. **컬럼 설명**: `info` 파라미터로 컬럼 설명 추가
3. **관계 정의**: `db.relationship()`으로 연관 관계 명시
4. **자동 생성 필드**: `server_default=db.FetchedValue()`로 DB 기본값 사용

---

## 10. 쿼리 작성 패턴

### 기본 조회: SQLAlchemy ORM 사용

```python
# ✅ 단순 조회
def find(self, id: str):
    session = Session()
    try:
        return session.query(User).filter(User.id == id).first()
    finally:
        session.close()


# ✅ 조건 필터링
def find_all(self, company_id: str = None, user_id: str = None):
    session = Session()
    try:
        query = session.query(User)
        if company_id is not None:
            query = query.filter(User.company_id == company_id)
        if user_id is not None:
            query = query.filter(User.user_id == user_id)
        return query.all()
    finally:
        session.close()
```

### JOIN 조회

```python
# ✅ JOIN 사용
def find_with_company(self, id: str):
    session = Session()
    try:
        return (
            session.query(User)
            .join(Company, User.company_id == Company.id)
            .filter(User.id == id)
            .first()
        )
    finally:
        session.close()
```

### Raw Query (예외적 사용)

```python
# ⚠️ 예외: 복잡한 집계/서브쿼리/윈도우 함수 등
def complex_report(self):
    session = Session()
    try:
        result = session.execute("""
            SELECT 
                user_id,
                COUNT(*) as total,
                SUM(amount) OVER (PARTITION BY company_id) as company_total
            FROM user
            WHERE status = 'active'
            GROUP BY company_id
        """)
        return result.fetchall()
    finally:
        session.close()
```

### 쿼리 작성 원칙

- **기본**: SQLAlchemy ORM 메서드 사용 (`query()`, `filter()`, `join()`)
- **JOIN 필요 시**: ORM의 `join()` 메서드 사용
- **Raw Query**: 가능하면 지양, 복잡도가 너무 높을 때만 예외 허용

---

## 11. 에러 처리

### Controller 레벨

```python
@router.post("")
def create(create_dto: CreateDto):
    try:
        return user_service.save(create_dto)
    except Exception as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)
```

### Service 레벨

```python
def save(self, create_dto: CreateDto):
    session = Session()
    try:
        # 중복 체크
        existing = session.query(User).filter(User.user_id == create_dto.user_id).first()
        if existing:
            raise Exception("이미 존재하는 사용자입니다")
        
        # 저장 로직
        stmt = insert(User).values(...)
        session.execute(stmt)
        session.commit()
        return self.find(key)
    except BaseException as e:
        session.rollback()
        raise e
    finally:
        session.close()


def find(self, id: str):
    session = Session()
    try:
        user = session.query(User).filter(User.id == id).first()
        if user is None:
            raise Exception("사용자를 찾을 수 없습니다")
        return user
    finally:
        session.close()
```

### 에러 처리 원칙

1. **Controller**: try-except로 에러 잡고, JSONResponse로 응답
2. **Service**: 의미있는 예외 메시지로 `raise Exception()` 
3. **세션 롤백**: 데이터 변경 작업 실패 시 반드시 `session.rollback()`

---

## 12. 외부 API 호출 패턴

### requests 사용 시 timeout 필수

```python
import requests


class ExternalApiService:
    def call_external_api(self, url: str, data: dict):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=data,
                timeout=30  # ✅ 반드시 timeout 설정
            )
            
            if response.status_code != 200:
                raise Exception(f"API 오류: {response.status_code}")
            
            return response.json()
        except requests.exceptions.Timeout:
            raise Exception("외부 서비스 응답 지연. 잠시 후 다시 시도해주세요.")
        except BaseException as e:
            raise e
```

### 외부 API 호출 원칙

1. **timeout 필수**: 모든 `requests` 호출에 timeout 설정 (권장: 30초)
2. **에러 처리**: 상태 코드 확인 및 적절한 예외 발생
3. **Timeout 예외**: `requests.exceptions.Timeout` 별도 처리 권장

---

## 13. 의존성 관리

### 타 도메인 Service 사용

```python
# ✅ 좋음: 필요한 Service만 import하여 사용
from src.company.company_service import CompanyService
from src.user.user_service import UserService


class FinancialAdvisorService:
    def __init__(self):
        self.company_service = CompanyService()
        self.user_service = UserService()

    def create_advisor(self, dto):
        company = self.company_service.find(dto.company_id)
        if company is None:
            raise Exception("회사 정보가 없습니다")
        # ...
```

### 순환 참조 방지

```python
# ❌ 나쁨: 순환 참조
# user_service.py
from src.company.company_service import CompanyService  # Company가 User를 import하면 순환

# ✅ 좋음: 필요한 곳에서만 import
# Controller에서 여러 Service를 조합
class UserController:
    def __init__(self):
        self.user_service = UserService()
        self.company_service = CompanyService()
```

### 의존성 관리 원칙

| 상황 | 해결 방법 |
|------|----------|
| **단순 조회** | 해당 Model을 직접 query |
| **Create/Update** | Service 메서드 재사용 |
| **여러 Service 조합** | Controller에서 조합 |
| **트랜잭션 필요** | 상위 Manager Service 생성 |

---

## 14. Docstring 작성

### 기본 원칙

Python의 강점 중 하나인 **Docstring**을 적극 활용합니다.

- 모든 **public 함수/메서드**에 docstring 작성
- IDE 자동완성, `help()`, API 문서 자동 생성에 활용됨
- **Google Style** docstring 형식 사용

### 주석 vs Docstring

| | 주석 (`#`) | Docstring (`"""`) |
|---|---|---|
| **용도** | 코드 내부 설명 (개발자 메모) | 함수/클래스/모듈 문서화 |
| **접근** | 코드에서만 보임 | `help()`, `__doc__`로 런타임 접근 가능 |
| **도구 지원** | 없음 | IDE 자동완성, API 문서 자동 생성 |

### Google Style Docstring

```python
def create_slack_message(
    product_name: str,
    original_question: str,
    max_token: int,
    model_name: str,
    reference_docs: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Slack 알림 메시지 생성

    Args:
        product_name: 제품명
        original_question: 원본 질문
        max_token: 예상 토큰수
        model_name: 사용 모델명
        reference_docs: 참조문서 목록

    Returns:
        포맷팅된 Slack 메시지 문자열

    Raises:
        ValueError: product_name이 유효하지 않을 때
    """
    ...
```

### Docstring 작성 기준

| 대상 | 필수 여부 | 설명 |
|------|----------|------|
| **Public 함수/메서드** | ✅ 필수 | 외부에서 호출되는 모든 함수 |
| **Private 함수** (`_` prefix) | 선택 | 복잡한 로직일 때만 |
| **클래스** | ✅ 필수 | 클래스 역할 설명 |
| **모듈** | 권장 | 파일 상단에 모듈 설명 |

### 좋은 예시 vs 나쁜 예시

```python
# ✅ 좋음: 명확한 설명과 파라미터 문서화
def detect_language(text: str) -> str:
    """
    텍스트의 언어를 감지

    Args:
        text: 감지할 텍스트

    Returns:
        언어 코드 (ko, en, ja, vi 등), 실패 시 "ko" 반환
    """
    ...


# ❌ 나쁨: 코드만 보고 알 수 있는 내용 반복
def detect_language(text: str) -> str:
    """
    detect_language 함수입니다.
    text를 받아서 언어를 반환합니다.
    """
    ...


# ❌ 나쁨: docstring 없음
def detect_language(text: str) -> str:
    return langid.classify(text)[0]
```

### IDE 활용

Docstring을 작성하면:

1. **함수 호출 시** 파라미터 설명이 자동으로 표시됨
2. **마우스 hover** 시 함수 설명 확인 가능
3. **Sphinx/MkDocs**로 API 문서 자동 생성 가능

```python
>>> help(detect_language)
detect_language(text: str) -> str
    텍스트의 언어를 감지

    Args:
        text: 감지할 텍스트

    Returns:
        언어 코드 (ko, en, ja, vi 등), 실패 시 "ko" 반환
```

---

## 요약

### 핵심 원칙

1. **Model 중심**: 1 Model = 1 Module = 1 Endpoint
2. **기본 CRUD**: 모든 엔드포인트는 기본 5개 CRUD 제공
3. **DTO 3종 세트**: create/update/get
4. **세션 관리**: try-except-finally로 세션 생성/종료 관리
5. **Controller에서 에러 처리**: try-except + JSONResponse
6. **외부 API 호출**: 반드시 timeout 설정
7. **쿼리는 단순하게**: ORM 우선, 복잡하면 JOIN, Raw는 최후
8. **Docstring 필수**: public 함수에 Google Style docstring 작성

### 네이밍 체크리스트

- [ ] Model: PascalCase (`User`, `Company`)
- [ ] Endpoint: snake_case 또는 kebab-case (`/user`, `/financial-advisor`)
- [ ] Folder: snake_case (`user/`, `financial_advisor_user/`)
- [ ] Controller/Service: PascalCase (`UserService`, `UserController`)
- [ ] 파일명: snake_case (`user_service.py`, `create_user_dto.py`)
- [ ] 함수/메서드: snake_case (`find_all()`, `get_current_user()`)
- [ ] 변수: snake_case (`user_service`, `company_id`)
