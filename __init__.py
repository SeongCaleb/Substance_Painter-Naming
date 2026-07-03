"""
Layer Organizer - 레이어에 물린 제네레이터/필터 리소스를 분석해서
자동으로 이름을 붙여주는 플러그인 (이미지 export 없이 메타데이터만 조회)

설치 위치: python/plugins/layer_organizer/__init__.py
"""

import time

import substance_painter as sp
import substance_painter.ui
import substance_painter.project
import substance_painter.textureset as ts
import substance_painter.layerstack as ls

# Painter 버전에 따라 PySide2 / PySide6 자동 분기
if sp.application.version_info() < (10, 1, 0):
    from PySide2 import QtWidgets
else:
    from PySide6 import QtWidgets

plugin_widgets = []


# ---------------------------------------------------------------------------
# 0. 분류 키워드 사전
#    - 리소스 원본 이름(resource_id.name) 기준이라 프로젝트/사람 안 가림
#    - CORE: 레이어가 "무엇을 표현하는지"를 결정하는 핵심 생성기
#    - MODIFIER: 위 결과를 다듬기만 하는 보정 필터 (블러, 히스토그램 등)
#      -> CORE가 하나라도 있으면 MODIFIER는 이름에서 무시됨
# ---------------------------------------------------------------------------

# 이름 길이 조절 옵션 -----------------------------------------------------
FALLBACK_MAX_LEN = 10   # 매칭 안 된 리소스명을 폴백으로 쓸 때 최대 글자 수
# ---------------------------------------------------------------------------

CORE_KEYWORDS = {
    "AO": ["ambient_occlusion", "ambientocclusion"],
    "커버쳐": ["curvature"],
    "라이트": ["light"],
    "그라데이션": ["gradient", "position_gradient"],
    "그런지": ["grunge"],
    "먼지": ["dirt", "grime"],
    "엣지": ["edge_wear", "edgewear", "edge_damage", "metal_edge"],
    "노이즈": ["noise", "perlin", "cell_noise"],
}

MODIFIER_KEYWORDS = {
    "블러": ["blur"],
    "히스토그램": ["histogram"],
    "레벨": ["levels"],
    "샤픈": ["sharpen"],
    "컬러밸런스": ["color_balance", "hcl", "anisotropic"],
}

# 박사님 개인 워크플로우 용어를 여기 채워서 쓰면 됨 (기본은 비워둠, CORE와 같은 우선순위로 취급)
PERSONAL_KEYWORDS = {
    # "나뭇결": ["wood_grain", "grunge_lac"],
    # "틈새": ["cavity"],
}

# 폴백 이름 정리 시 제거할 흔한 접두어/잡음 토큰
NOISE_TOKENS = ["mg", "sp", "map", "generator", "filter"]


def match_keyword(name_lower, keyword_dict):
    for label, keywords in keyword_dict.items():
        for kw in keywords:
            if kw in name_lower:
                return label
    return None


def clean_fallback_name(resource_name):
    """매칭 안 된 리소스 이름을 짧고 깔끔하게 정리"""
    base = resource_name.split("/")[-1]
    parts = [p for p in base.split("_") if p and not p.isdigit() and p.lower() not in NOISE_TOKENS]
    short = "".join(parts) if parts else base
    return short[:FALLBACK_MAX_LEN]


def classify_resource_name(resource_name):
    """리소스 이름(resource_id.name) 하나를 (등급, 라벨) 튜플로 분류.
    등급: 'core' > 'modifier' > 'fallback' 순으로 우선순위를 가짐
    """
    name_lower = resource_name.lower()

    label = match_keyword(name_lower, PERSONAL_KEYWORDS)
    if label:
        return "core", label

    label = match_keyword(name_lower, CORE_KEYWORDS)
    if label:
        return "core", label

    label = match_keyword(name_lower, MODIFIER_KEYWORDS)
    if label:
        return "modifier", label

    return "fallback", clean_fallback_name(resource_name)


# ---------------------------------------------------------------------------
# 1. 레이어 트리 순회
# ---------------------------------------------------------------------------
def get_all_nodes(nodes):
    """폴더 안까지 재귀적으로 들어가서 모든 레이어 노드를 평탄화한 리스트로 반환"""
    result = []
    for n in nodes:
        result.append(n)
        if hasattr(n, "sub_layers"):
            try:
                children = n.sub_layers()
                if children:
                    result.extend(get_all_nodes(children))
            except Exception:
                pass
    return result


# ---------------------------------------------------------------------------
# 2. 레이어 하나를 분석해서 라벨 목록 생성
# ---------------------------------------------------------------------------
def classify_node(node, log_widget):
    node_type = node.get_type()

    valid_types = (ls.NodeType.PaintLayer, ls.NodeType.FillLayer)
    if node_type not in valid_types:
        return []  # 폴더 등은 분류 대상 아님, 이름 유지

    has_mask = False
    try:
        has_mask = node.has_mask()
    except Exception:
        pass

    effects = []
    if has_mask:
        try:
            effects = node.mask_effects()
        except Exception as e:
            log_widget.append("  (마스크 이펙트 조회 실패: {})".format(e))

    total_effect_count = len(effects)  # Levels 같은 리소스 없는 조정 이펙트도 "추가로 뭔가 얹었다"는 신호로 셈

    core_labels = []
    modifier_labels = []
    fallback_labels = []

    for eff in effects:
        try:
            src = eff.get_source()  # 마스크 안이라 mono channel이라 인자 불필요
            if not (src and src.resource_id):
                continue
            tier, label = classify_resource_name(src.resource_id.name)
            if tier == "core" and label not in core_labels:
                core_labels.append(label)
            elif tier == "modifier" and label not in modifier_labels:
                modifier_labels.append(label)
            elif tier == "fallback" and label not in fallback_labels:
                fallback_labels.append(label)
        except Exception:
            # 이펙트 종류에 따라 get_source가 없을 수 있음 (예: PaintEffectNode, Levels 등 조정 이펙트)
            continue

    # 대표 라벨 선정: core > modifier > fallback 우선순위
    if core_labels:
        primary = core_labels[0]
    elif modifier_labels:
        primary = modifier_labels[0]
    elif fallback_labels:
        primary = fallback_labels[0]
    else:
        # 이펙트를 하나도 못 찾음 -> 마스크 유무 상관없이 베이스로 간주
        if node_type == ls.NodeType.FillLayer:
            return ["베이스"]
        return []

    # 이펙트가 딱 1개면 이름 그대로, 2개 이상이면 "~활용"으로 표시
    if total_effect_count > 1:
        return ["{}활용".format(primary)]
    return [primary]


# ---------------------------------------------------------------------------
# 3. 전체 레이어 일괄 처리 (export 없이 메타데이터만 조회하므로 매우 빠름)
# ---------------------------------------------------------------------------
def process_all_layers(log_widget, dry_run=True):
    """
    dry_run=True  : 실제로 이름을 바꾸지 않고 로그에만 "이렇게 바뀔 예정"을 출력
    dry_run=False : 실제로 node.set_name()까지 적용
    """
    if not substance_painter.project.is_open():
        log_widget.append("프로젝트가 열려있지 않습니다.")
        return

    stack = ts.get_active_stack()
    root_nodes = ls.get_root_layer_nodes(stack)
    all_nodes = get_all_nodes(root_nodes)

    if not all_nodes:
        log_widget.append("레이어가 없습니다.")
        return

    mode_text = "미리보기 (실제 변경 없음)" if dry_run else "실제 적용"
    log_widget.append("총 {}개 레이어 처리 시작... [{}]".format(len(all_nodes), mode_text))
    QtWidgets.QApplication.processEvents()

    start_time = time.time()
    changed_count = 0

    for i, node in enumerate(all_nodes):
        try:
            original_name = node.get_name()
            labels = classify_node(node, log_widget)

            if not labels:
                # 분류 안 된 레이어(폴더, 이펙트 없는 페인트 레이어 등)는 건드리지 않음
                continue

            new_name = "_".join(labels)
            if new_name == original_name:
                continue

            if not dry_run:
                node.set_name(new_name)

            changed_count += 1
            log_widget.append("[{}/{}] {} -> {}".format(i + 1, len(all_nodes), original_name, new_name))

        except Exception as e:
            log_widget.append("[{}/{}] 에러: {}".format(i + 1, len(all_nodes), str(e)))

    elapsed = time.time() - start_time
    log_widget.append("완료! {}개 레이어 변경 대상, 총 {:.2f}초 소요.".format(changed_count, elapsed))


# ---------------------------------------------------------------------------
# 5. 플러그인 UI
# ---------------------------------------------------------------------------
panel_instance = None  # 패널이 이미 만들어졌는지 추적 (중복 생성 방지)
show_action = None


def _build_panel():
    global panel_instance

    panel = QtWidgets.QWidget()
    panel.setObjectName("layer_organizer_panel")  # 도킹 위치를 Painter가 제대로 기억하게 함
    panel.setWindowTitle("Layer Organizer")
    layout = QtWidgets.QVBoxLayout(panel)

    preview_button = QtWidgets.QPushButton("미리보기 (이름 변경 없이 확인만)")
    apply_button = QtWidgets.QPushButton("실제 이름 적용")
    log_widget = QtWidgets.QTextEdit()
    log_widget.setReadOnly(True)

    layout.addWidget(preview_button)
    layout.addWidget(apply_button)
    layout.addWidget(log_widget)

    preview_button.clicked.connect(lambda: process_all_layers(log_widget, dry_run=True))
    apply_button.clicked.connect(lambda: process_all_layers(log_widget, dry_run=False))

    substance_painter.ui.add_dock_widget(panel)
    plugin_widgets.append(panel)
    panel_instance = panel
    return panel


def show_panel():
    """패널이 숨어있거나 아직 없으면 새로 만들거나 강제로 앞으로 가져옴.
    파일 수정 후 재로드했거나, 재시작 후 패널이 안 보일 때 이 메뉴로 복구 가능."""
    global panel_instance
    if panel_instance is None:
        _build_panel()
    panel_instance.show()
    panel_instance.raise_()
    panel_instance.activateWindow()


import traceback

import substance_painter.logging as sp_log


def start_plugin():
    global show_action

    sp_log.info("layer_organizer: start_plugin() 호출됨")

    try:
        _build_panel()
        sp_log.info("layer_organizer: 패널 생성 완료")
    except Exception:
        sp_log.error("layer_organizer 패널 생성 실패:\n" + traceback.format_exc())
        return  # 패널 생성 실패하면 메뉴 액션은 시도하지 않음

    # Python 메뉴에 "Layer Organizer 보이기" 액션 추가
    # -> 패널이 숨어서 안 보일 때 콘솔 없이 클릭 한 번으로 복구 가능
    try:
        show_action = QtWidgets.QAction("Layer Organizer 보이기")
        show_action.triggered.connect(show_panel)
        substance_painter.ui.add_action(
            substance_painter.ui.ApplicationMenu.Plugins,
            show_action
        )
        plugin_widgets.append(show_action)
        sp_log.info("layer_organizer: 메뉴 액션 추가 완료")
    except Exception:
        sp_log.error("layer_organizer 메뉴 액션 추가 실패:\n" + traceback.format_exc())


def close_plugin():
    global panel_instance, show_action
    sp_log.info("layer_organizer: close_plugin() 호출됨, 위젯 {}개 정리".format(len(plugin_widgets)))
    for widget in plugin_widgets:
        substance_painter.ui.delete_ui_element(widget)
    plugin_widgets.clear()
    panel_instance = None
    show_action = None


if __name__ == "__main__":
    start_plugin()
