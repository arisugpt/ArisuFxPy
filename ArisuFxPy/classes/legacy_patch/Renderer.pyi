from ArisuFxPy.classes import PPtr
from ArisuFxPy.classes.generated import Component
from ArisuFxPy.classes.legacy_patch import GameObject

class Renderer(Component):
    m_GameObject: PPtr[GameObject]

    def export(self, export_dir: str) -> None: ...
