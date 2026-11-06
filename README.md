> **Mirror note (2026-11-06):** The source code, documentation, and 22 reference images are mirrored here. The following three binary 3D files exceed the GitHub content-read limit exposed by the connected transfer API and are therefore not copied into this mirror yet. They remain available in the upstream repository:
> - [Kirsch_Home_3D_Jutsu.blend](https://github.com/highsun9941/AD/blob/main/Kirsch_Home_3D_Jutsu.blend)
> - [Kirsch_Home_3D_Jutsu.glb](https://github.com/highsun9941/AD/blob/main/Kirsch_Home_3D_Jutsu.glb)
> - [Kirsh_Home_Product_Preview.glb](https://github.com/highsun9941/AD/blob/main/product-preview/Kirsh_Home_Product_Preview.glb)

# 키르시홈 3D Jutsu 광고 샘플

> [침구 제품 3D 미리보기](product-preview/)에서 제품 사진 22장을 바탕으로 만든 쇼룸과 Higgsfield MCP 연결 방법을 확인할 수 있습니다.

숲속 나무집과 4색 침대, 하트 쿠션을 안고 떠오르는 인물, 흰색으로 전환되는 키르시홈 엔드카드로 구성한 24초 광고 샘플입니다. 장면은 16:9, 24fps이며 인물과 침구는 절차적으로 만든 샘플 모델입니다. 엔드카드에는 임시 키르시홈 워드마크가 들어 있습니다.

## 파일

| 파일 | 용도 |
| --- | --- |
| [Kirsch_Home_3D_Jutsu.glb](Kirsch_Home_3D_Jutsu.glb) | 3D Jutsu 웹에서 새 장면에 가져올 파일. 모델과 오브젝트 동작이 하나의 24초 애니메이션 클립에 들어 있습니다. |
| [Kirsch_Home_3D_Jutsu.blend](Kirsch_Home_3D_Jutsu.blend) | Blender 편집본. 카메라 컷, 조명, 재질, 키프레임, 흰색 페이드와 엔드카드를 포함합니다. |
| [scene/](scene/) | Higgsfield MCP로 전체 장면을 새 프로젝트에 재현하는 데 사용한 Blender Python 코드입니다. |

GLB를 가져올 때는 3D Jutsu에서 새 장면을 열고 파일을 선택한 뒤 24초 타임라인을 재생하세요. 카메라 컷과 페이드까지 같은 방식으로 재현하려면 아래의 MCP 실행 순서를 사용하세요.

## Higgsfield MCP에서 새 프로젝트로 재현

다른 세션에서 코딩 에이전트에게 `highsun9941/AD`의 이 절에 따라 새 3D Jutsu 프로젝트에 장면을 복원해 달라고 요청하세요. 에이전트는 대상 계정의 Higgsfield MCP에 연결되어 있어야 합니다.

1. `get_preset_instructions`에서 `/3d-jutsu`의 실행 지침을 불러옵니다.
2. `scene_builder_3d_create_project`로 새 비공개 프로젝트를 만듭니다. 첫 스크립트는 씬의 오브젝트와 컬렉션을 초기화하므로 **새 빈 프로젝트에서만** 실행합니다.
3. 반환된 `projectId`로 `scene_builder_3d_get_project`와 `scene_builder_3d_query_python`을 실행합니다. 첫 쓰기 전에는 씬이 비어 있는지 확인합니다.
4. 아래 스크립트를 순서대로 한 개씩 실행합니다. 각 파일의 **전체 UTF-8 텍스트**를 `scene_builder_3d_run_python`의 `code`에 넣습니다. 매번 새 읽기 쿼리의 `revisionBefore`와 `sceneSequenceAfter`를 각각 `revision`과 `expectedSceneSequence`로 사용합니다.
5. 작업이 진행 중이면 동일한 `projectId`와 `operationId`로 `scene_builder_3d_get_operation`을 확인합니다. 작업이 `succeeded`로 끝난 뒤 다음 쓰기를 시작합니다. 응답이 불확실하면 같은 작업 ID로 상태를 확인합니다.
6. 아래 타임라인을 확인하고, 마지막 작업에서 반환된 `revisionAfter`로 `scene_builder_3d_show_scene`을 호출합니다. 이 단계까지 장면과 애니메이션을 재현할 수 있습니다. AI 영상 생성은 별도 작업입니다.

| 순서 | 스크립트 | 결과 |
| --- | --- | --- |
| 1 | [01_build_scene.py](scene/01_build_scene.py) | 나무집, 실내, 숲, 카메라와 기본 조명을 배치합니다. |
| 2 | [02_animate_scene.py](scene/02_animate_scene.py) | 침대와 캐릭터를 완성하고 키프레임, 카메라 컷, 엔드카드를 추가합니다. |
| 3 | [03_refine_cameras.py](scene/03_refine_cameras.py) | 문 통과, 제품, 쿠션, 비행 컷의 최종 구도를 적용합니다. |

원본 장면은 Higgsfield의 Blender 5.2 런타임에서 만들었습니다. Blender 편집본은 4.3.2에서 열 수 있습니다.

## 재현 확인

| 시간 | 프레임 | 확인할 내용 |
| --- | ---: | --- |
| 0.0초 | 1 | 여성이 나무집으로 걸어갑니다. |
| 6.0초 | 145 | 빨강 침대 제품 컷이 시작됩니다. |
| 9.0초 | 217 | 주황 침대로 바뀝니다. |
| 12.0초 | 289 | 노랑 침대로 바뀝니다. |
| 15.0초 | 361 | 초록 침대로 바뀝니다. |
| 약 17.9초 | 430 | 여성이 하트 쿠션을 집습니다. |
| 약 19.8초 | 477 | 지붕 위로 올라가는 컷이 시작됩니다. |
| 약 21.9초 | 527 | 흰색 엔드카드가 시작되고 워드마크가 나타납니다. |

최종 씬은 1–576 프레임, 24fps, 카메라 6대입니다. 전환 직전과 직후 프레임을 비교하면 침대 색이 3초 간격으로 바뀌는지 확인할 수 있습니다.

### 원본 파일 체크섬

```text
2c4ed91568c78e4be98736b977a35e0dc9df962659debdf0f022954fac54798b  Kirsch_Home_3D_Jutsu.glb
1b27fa0b889000f3090ecfb5d1d9cc1e50c5138b33203c1a0b37232fa691ee3f  Kirsch_Home_3D_Jutsu.blend
```
