# Layer Organizer for Substance 3D Painter

레이어에 물린 제네레이터/필터 리소스를 분석해서 자동으로 이름을 붙여주는 Substance 3D Painter 플러그인입니다.
이미지 export 없이 레이어 스택 메타데이터만 조회하기 때문에 레이어가 수십 개여도 빠르게 처리됩니다.

## 주요 기능

- 마스크에 물린 이펙트(제네레이터/필터)의 실제 리소스 이름을 기준으로 분류하므로, 사람이 레이어 이름을 뭐라고 바꿔놨든 정확하게 인식합니다.
- 이펙트가 하나면 그 이름 그대로(`AO`, `그런지`), 여러 개가 겹치면 대표 이펙트 + `활용` 접미사(`그런지활용`, `커버쳐활용`)를 붙입니다.
- 이펙트가 전혀 없는 Fill 레이어는 `베이스`로 분류합니다.
- **미리보기 모드**: 실제로 이름을 바꾸기 전에 어떻게 바뀔지 로그로 먼저 확인할 수 있습니다.
- 폴더 안에 중첩된 레이어까지 재귀적으로 처리합니다.

## 설치 방법

1. 이 저장소의 `layer_organizer` 폴더를 통째로 복사합니다.
2. Substance 3D Painter의 Python 플러그인 폴더에 붙여넣습니다.
   - **Windows**: `문서\Adobe\Adobe Substance 3D Painter\python\plugins\`
   - **macOS**: `~/Documents/Adobe/Adobe Substance 3D Painter/python/plugins/`
   - Painter에서 `Python` 메뉴 → `Plugins Folder`를 클릭하면 정확한 경로가 바로 열립니다.
3. 최종 경로가 `.../python/plugins/layer_organizer/__init__.py`가 되어야 합니다.
4. Painter를 재시작하거나 `Python` 메뉴 → `Reload Plugins Folder`를 클릭합니다.
5. `Python` 메뉴에서 `layer_organizer`에 체크가 되어 있는지 확인합니다.

## 사용 방법

1. 프로젝트를 열고 "Layer Organizer" 도킹 패널을 확인합니다 (안 보이면 `Python` 메뉴 → `layer_organizer` 체크 해제 후 재체크).
2. **"미리보기 (이름 변경 없이 확인만)"** 버튼을 눌러 어떻게 이름이 바뀔지 로그로 확인합니다.
3. 결과가 마음에 들면 **"실제 이름 적용"** 버튼을 눌러 실제로 반영합니다.

## 커스터마이징

`__init__.py` 상단의 키워드 사전을 수정해서 원하는 대로 확장할 수 있습니다.

- `CORE_KEYWORDS`: 레이어의 정체성을 결정하는 핵심 생성기 (AO, 커버쳐, 그런지 등)
- `MODIFIER_KEYWORDS`: 위 결과를 다듬기만 하는 보정 필터 (블러, 히스토그램 등)
- `PERSONAL_KEYWORDS`: 개인/스튜디오 워크플로우에서만 쓰는 리소스 이름을 여기에 추가하면 됩니다.

```python
PERSONAL_KEYWORDS = {
    "나뭇결": ["wood_grain", "grunge_lac"],
    "틈새": ["cavity"],
}
```

## 알려진 제한 사항

- 마스크 안의 이펙트만 분석합니다 (레이어 콘텐츠 자체에 걸린 필터는 현재 버전에서 다루지 않습니다).
- 손으로 직접 칠한 마스크(제네레이터/필터가 안 걸린 경우)는 자동 분류 대상이 아니며 원래 이름을 유지합니다.
- Substance 3D Painter의 Python API 세부 동작은 버전마다 다를 수 있습니다. 이슈가 발생하면 Painter 버전과 함께 제보해 주세요.

## 요구 사항

- Substance 3D Painter (Python API 지원 버전, PySide2 또는 PySide6 자동 감지)

## 라이선스

MIT License (LICENSE 파일 참고)
