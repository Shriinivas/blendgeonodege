# run this script from text editor or install it as an addon
# switch to Geonode Game workspace (if not available switch to Layout and hide all panels and windows other than 3d viewport)
# press z and switch to render mode
# press n to open side panel of 3d viewport, click Geonode Engine tab, click start and close the panel by pressing n
# press enter to start playing the game; you can pause with spacebar

bl_info = {
    "name": "Node Engine Controller",
    "author": "Node Dev",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > Geonode Engine",
    "description": "Start, stop, and configure the Geometry Nodes Game Engine.",
    "category": "3D View",
}

import bpy
import time

# ==========================================
# VIRTUAL KEYMAP
# ==========================================
VIRTUAL_KEYMAP = {
    "input_x_axis": {"pos": {"RIGHT_ARROW", "D"}, "neg": {"LEFT_ARROW", "A"}},
    "input_y_axis": {"pos": {"UP_ARROW", "W"}, "neg": {"DOWN_ARROW", "S"}},
    "input_action": {"RET", "NUMPAD_ENTER"},
    "input_action_2": {"LEFTMOUSE", "F"},
}

MAPPED_KEYS = set()
for mapping in VIRTUAL_KEYMAP.values():
    if isinstance(mapping, dict):
        MAPPED_KEYS.update(mapping.get("pos", set()))
        MAPPED_KEYS.update(mapping.get("neg", set()))
    elif isinstance(mapping, set):
        MAPPED_KEYS.update(mapping)

SUPPORTED_INPUTS = {
    "input_x_axis",
    "input_y_axis",
    "input_action",
    "input_action_2",
    "mouse_x",
    "mouse_y",
    "mouse_dx",
    "mouse_dy",
    "delta_time",
}


def setup_modifier_drivers(obj):
    if not obj:
        return set()

    mod = next((m for m in obj.modifiers if m.type == "NODES"), None)
    if not mod or not mod.node_group:
        return set()

    active_inputs = set()
    for item in mod.node_group.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT":
            prop_name = item.name
            identifier = item.identifier

            if prop_name in SUPPORTED_INPUTS:
                active_inputs.add(prop_name)
                if prop_name not in obj:
                    obj[prop_name] = 0.0

                data_path = f'["{identifier}"]'
                try:
                    mod.driver_remove(data_path)
                except TypeError:
                    pass

                fcurve = mod.driver_add(data_path)
                driver = fcurve.driver
                driver.type = "AVERAGE"
                var = driver.variables.new()
                var.name = "var"
                var.type = "SINGLE_PROP"
                target = var.targets[0]
                target.id_type = "OBJECT"
                target.id = obj
                target.data_path = f'["{prop_name}"]'

    return active_inputs


# ==========================================
# PROPERTIES & UI
# ==========================================
class EngineProperties(bpy.types.PropertyGroup):
    target_object: bpy.props.PointerProperty(
        name="Engine Object",
        type=bpy.types.Object,
        description="The object running the main game Geometry Nodes",
    )
    capture_keyboard: bpy.props.BoolProperty(
        name="Capture Keyboard",
        default=True,
        description="Capture mapped keys (blocks standard Blender shortcuts for those keys)",
    )
    capture_mouse: bpy.props.BoolProperty(
        name="Capture Mouse Clicks",
        default=False,
        description="Capture mouse clicks (blocks standard Blender 3D cursor/selection)",
    )
    is_running: bpy.props.BoolProperty(default=False)


class VIEW3D_PT_engine_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Geonode Engine"
    bl_label = "GeoNodes Engine"

    def draw(self, context):
        layout = self.layout
        props = context.scene.engine_props

        box = layout.box()
        box.prop(props, "target_object")

        box = layout.box()
        box.label(text="Input Capturing:", icon="COMMUNITY")
        box.prop(props, "capture_keyboard")
        box.prop(props, "capture_mouse")

        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.5

        if not props.is_running:
            row.operator("engine.start", icon="PLAY", text="Start Engine")
        else:
            row.operator("engine.stop", icon="PAUSE", text="Stop Engine")

        layout.operator("engine.reset", icon="REW", text="Reset to Frame 1")


# ==========================================
# OPERATORS
# ==========================================
class ENGINE_OT_start(bpy.types.Operator):
    bl_idname = "engine.start"
    bl_label = "Start Engine"

    def execute(self, context):
        props = context.scene.engine_props

        # Auto-find Master_Engine if left blank!
        if not props.target_object:
            if "Master_Engine" in bpy.data.objects:
                props.target_object = bpy.data.objects["Master_Engine"]
            else:
                self.report({"WARNING"}, "Please assign an Engine Object first!")
                return {"CANCELLED"}

        props.is_running = True
        bpy.ops.wm.engine_input()
        return {"FINISHED"}


class ENGINE_OT_stop(bpy.types.Operator):
    bl_idname = "engine.stop"
    bl_label = "Stop Engine"

    def execute(self, context):
        context.scene.engine_props.is_running = False
        return {"FINISHED"}


class ENGINE_OT_reset(bpy.types.Operator):
    bl_idname = "engine.reset"
    bl_label = "Reset (Frame 1)"

    def execute(self, context):
        context.scene.frame_set(1)
        return {"FINISHED"}


class EngineInputModal(bpy.types.Operator):
    bl_idname = "wm.engine_input"
    bl_label = "Engine Input Handler"

    _timer = None
    _active_keys = None
    _consumed_clicks = None
    _active_inputs = None
    _last_time = 0.0
    _mouse_x = 0.0
    _mouse_y = 0.0
    _mouse_dx = 0.0
    _mouse_dy = 0.0

    def modal(self, context, event):
        props = context.scene.engine_props

        # Stop check from UI button
        if not props.is_running:
            return self.cancel(context)

        # Stop check from ESC key
        if event.type == "ESC":
            props.is_running = False
            return self.cancel(context)

        hovered_area, hovered_region = None, None
        for area in context.window.screen.areas:
            if (
                area.x <= event.mouse_x <= area.x + area.width
                and area.y <= event.mouse_y <= area.y + area.height
            ):
                hovered_area = area
                for region in area.regions:
                    if (
                        region.x <= event.mouse_x <= region.x + region.width
                        and region.y <= event.mouse_y <= region.y + region.height
                    ):
                        if hovered_region is None or region.type != "WINDOW":
                            hovered_region = region
                break

        in_3d_canvas = (
            hovered_area
            and hovered_area.type == "VIEW_3D"
            and hovered_region
            and hovered_region.type == "WINDOW"
        )
        is_mouse_event = event.type.endswith("MOUSE") and event.type != "MOUSEMOVE"

        # 1. Track Mouse Movement (Always active so game can read coordinates if needed, pass through to Blender)
        if event.type == "MOUSEMOVE":
            if in_3d_canvas:
                nx = (
                    (event.mouse_x - hovered_region.x) / hovered_region.width
                ) * 2.0 - 1.0
                ny = (
                    (event.mouse_y - hovered_region.y) / hovered_region.height
                ) * 2.0 - 1.0
                self._mouse_dx, self._mouse_dy = nx - self._mouse_x, ny - self._mouse_y
                self._mouse_x, self._mouse_y = nx, ny
            return {"PASS_THROUGH"}

        # 2. Track Keys and Mouse Buttons
        if event.value == "PRESS":
            self._active_keys.add(event.type)
            if event.type in MAPPED_KEYS:
                if is_mouse_event and props.capture_mouse and in_3d_canvas:
                    self._consumed_clicks.add(event.type)
                    return {"RUNNING_MODAL"}
                elif not is_mouse_event and props.capture_keyboard:
                    return {"RUNNING_MODAL"}

        elif event.value == "RELEASE":
            self._active_keys.discard(event.type)
            if event.type in MAPPED_KEYS:
                if (
                    is_mouse_event
                    and props.capture_mouse
                    and event.type in self._consumed_clicks
                ):
                    self._consumed_clicks.discard(event.type)
                    return {"RUNNING_MODAL"}
                elif not is_mouse_event and props.capture_keyboard:
                    return {"RUNNING_MODAL"}

        # 3. Game Tick (60Hz Timer)
        if event.type == "TIMER":
            obj = props.target_object
            if not obj:
                return {"PASS_THROUGH"}

            dt = (current_time := time.perf_counter()) - self._last_time
            self._last_time = current_time
            needs_update = False

            if "input_x_axis" in self._active_inputs:
                new_val = float(
                    bool(self._active_keys & VIRTUAL_KEYMAP["input_x_axis"]["pos"])
                ) - float(
                    bool(self._active_keys & VIRTUAL_KEYMAP["input_x_axis"]["neg"])
                )
                if obj["input_x_axis"] != new_val:
                    obj["input_x_axis"], needs_update = new_val, True

            if "input_y_axis" in self._active_inputs:
                new_val = float(
                    bool(self._active_keys & VIRTUAL_KEYMAP["input_y_axis"]["pos"])
                ) - float(
                    bool(self._active_keys & VIRTUAL_KEYMAP["input_y_axis"]["neg"])
                )
                if obj["input_y_axis"] != new_val:
                    obj["input_y_axis"], needs_update = new_val, True

            if "input_action" in self._active_inputs:
                new_val = int(bool(self._active_keys & VIRTUAL_KEYMAP["input_action"]))
                if obj["input_action"] != new_val:
                    obj["input_action"], needs_update = new_val, True

            if "input_action_2" in self._active_inputs:
                new_val = int(
                    bool(self._active_keys & VIRTUAL_KEYMAP["input_action_2"])
                )
                if obj["input_action_2"] != new_val:
                    obj["input_action_2"], needs_update = new_val, True

            if "mouse_x" in self._active_inputs and (
                self._mouse_dx != 0.0 or self._mouse_dy != 0.0
            ):
                obj["mouse_x"], obj["mouse_y"] = self._mouse_x, self._mouse_y
                obj["mouse_dx"], obj["mouse_dy"] = self._mouse_dx, self._mouse_dy
                needs_update = True

            if "delta_time" in self._active_inputs:
                obj["delta_time"] = dt

            self._mouse_dx = self._mouse_dy = 0.0
            if needs_update:
                obj.update_tag()

        return {"PASS_THROUGH"}

    def execute(self, context):
        props = context.scene.engine_props
        self._active_keys, self._consumed_clicks = set(), set()
        self._active_inputs = setup_modifier_drivers(props.target_object)
        self._last_time = time.perf_counter()

        context.scene.frame_end = 300000
        context.scene.frame_set(1)

        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.016, window=context.window)
        wm.modal_handler_add(self)
        self.report({"INFO"}, "Engine Started")
        return {"RUNNING_MODAL"}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)

        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)

        self.report({"INFO"}, "Engine Stopped")
        return {"CANCELLED"}


# ==========================================
# REGISTRY
# ==========================================
classes = (
    EngineProperties,
    VIEW3D_PT_engine_panel,
    ENGINE_OT_start,
    ENGINE_OT_stop,
    ENGINE_OT_reset,
    EngineInputModal,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Register the Scene property, but do NOT access bpy.data here!
    bpy.types.Scene.engine_props = bpy.props.PointerProperty(type=EngineProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.engine_props


if __name__ == "__main__":
    register()
