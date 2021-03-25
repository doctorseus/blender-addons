# templates: https://github.com/dfelinto/blender/tree/master/release/scripts/templates_py
import math
import itertools

import bpy
import bmesh
from bpy.types import WorkSpaceTool
from bpy.props import IntProperty, FloatProperty
from bpy_extras.view3d_utils import region_2d_to_vector_3d, region_2d_to_location_3d

bl_info = {
    "name": "Face color picker",
    "description": "Assign individual faces to distinct uv areas.",
    "author": "doctorseus",
    "version": (1, 1),
    "blender": (2, 92, 0),
    "location": "UV Editor > UV Edit Mode menu",
    "warning": "", # used for warning icon and text in add-ons panel
    "wiki_url": "https://github.com/doctorseus/blender-addons",
    "tracker_url": "https://github.com/doctorseus/blender-addons",
    "support": "COMMUNITY",
    "category": "UV"
}


def main(operator, context, event):
    x, y = event.mouse_region_x, event.mouse_region_y

    # mouse position in uv space
    uv_x, uv_y = bpy.context.region.view2d.region_to_view(x, y)

    if uv_x < 0 or uv_x > 1 or uv_y < 0 or uv_y > 1:
        operator.report({'ERROR'}, "Selected uv region out of bounds")
        return

    # main selected object
    # obj = context.active_object

    box_width = 1.0 / operator.xsteps
    box_height = 1.0 / operator.ysteps

    box_x = math.floor(uv_x / box_width)
    box_y = math.floor(uv_y / box_height)

    uv_padding_x = box_width * operator.padding
    uv_padding_y = box_height * operator.padding

    # CCW
    uv_corners = [
        (box_width * box_x + uv_padding_x, box_height * (box_y + 1) - uv_padding_y),  # top, left
        (box_width * box_x + uv_padding_x, box_height * box_y + uv_padding_y),        # bottom, left
        (box_width * (box_x + 1) - uv_padding_x, box_height * box_y + uv_padding_y),  # bottom, right
        (box_width * (box_x + 1) - uv_padding_x, box_height * (box_y + 1) - uv_padding_y),  # top, right
    ]

    # all selected objects
    for obj in context.selected_objects:
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        uv_layer = bm.loops.layers.uv.verify()  # selected active uv layer (TODO: Maybe fix the layer?)

        # adjust uv coordinates
        for face in bm.faces:
            if face.select:  # only active vaces
                # print(len(face.loops))
                # this can reach larger then 4?!#

                # we just assign corners in a loop
                idx = 0
                for loop in face.loops:
                    loop_uv = loop[uv_layer]  # select active uv vertices

                    # set uv of each vertex
                    loop_uv.uv = uv_corners[idx]

                    idx += 1
                    if idx >= 4:
                        idx = 0

                    # loop.vert.co.xy - xy position of the vertex

        bmesh.update_edit_mesh(me)


class UVSelectFaceColorOperator(bpy.types.Operator):
    bl_idname = "uv.select_face_color"
    bl_label = "Simple UV Operator"
    bl_options = {'REGISTER', 'UNDO'}
    
    xsteps: IntProperty(
        name="X Subdivisions",
        description="X Subdivisions",
        min=1, default=16,
    )
    
    ysteps: IntProperty(
        name="Y Subdivisions",
        description="Y Subdivisions",
        min=1, default=16,
    )
    
    padding: FloatProperty(
        name="Padding",
        description="Box Depth",
        min=0, max=1,
        default=0.1,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT'

    #  def execute(self, context):
    #    main(context)
    #    return {'FINISHED'}

    def invoke(self, context, event):
        main(self, context, event)
        return {'FINISHED'}


class UVFaceColorPicker(WorkSpaceTool):
    bl_space_type = 'IMAGE_EDITOR'
    bl_context_mode = 'UV'

    bl_idname = "uv.uv_face_color_picker"
    bl_label = "Face Color Picker"
    bl_description = ("")

    bl_icon = "brush.gpencil_draw.fill"  # brush.gpencil_draw.fill / brush.gpencil_draw.tint
    bl_widget = None
    bl_keymap = (
        ("uv.select_face_color", {"type": 'LEFTMOUSE', "value": 'PRESS'}, {"properties": []}),
    )

    def draw_settings(context, layout, tool):
        props = tool.operator_properties("uv.select_face_color")
        layout.prop(props, "xsteps")
        layout.prop(props, "ysteps")
        layout.prop(props, "padding")


# Original NewImage Op https://github.com/blender/blender/blob/master/source/blender/editors/space_image/image_ops.c#L2436

class OPDrawColorPalette(bpy.types.Operator):
    bl_idname = "image.draw_color_palette"
    bl_label = "Draw Color Palette"
    bl_options = {'UNDO'}

    xsteps: IntProperty(name="Columns", min=1, default=16)
    ysteps: IntProperty(name="Rows", min=1, default=16)

    def execute(self, context):
        for area in bpy.context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                image = area.spaces.active.image

                if image is None:
                    self.report({'ERROR'}, "No image found")
                    return {'FINISHED'}

                colors = [(c.color.r, c.color.g, c.color.b) for c in bpy.context.tool_settings.image_paint.palette.colors]
                colors_max = len(colors)

                image_width = image.size[0]
                image_height = image.size[1]

                step_width = image_width / self.xsteps
                step_height = image_height / self.ysteps

                def get_pixel(idx):
                    x = idx % image_width
                    y = image_height - int(idx / image_width)
                    return x, y

                def get_box_color(coord):
                    x = coord[0]
                    y = coord[1]

                    box_x = int(x / step_width)
                    box_y = int(y / step_height)

                    box_color = box_x + (box_y * self.xsteps)

                    if box_color < colors_max:
                        color = colors[box_color]
                    else:
                        color = (0, 0, 0)

                    return color[0], color[1], color[2], 1

                pixels = [get_box_color(get_pixel(idx)) for idx in range(0, image_width * image_height)]
                pixels = list(itertools.chain(*pixels))

                image.pixels = pixels

        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(self, "xsteps")
        layout.prop(self, "ysteps")

        settings = context.tool_settings.image_paint
        layout.template_ID(settings, "palette")
        layout.template_palette(settings, "palette", color=True)


def image_menu_func(self, context):
    for area in bpy.context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            if area.spaces.active.image is not None:
                self.layout.operator(OPDrawColorPalette.bl_idname)


def register():
    bpy.utils.register_class(UVSelectFaceColorOperator)
    bpy.utils.register_tool(UVFaceColorPicker, separator=True, group=True)
    bpy.utils.register_class(OPDrawColorPalette)
    bpy.types.IMAGE_MT_image.append(image_menu_func)


def unregister():
    bpy.utils.unregister_class(UVSelectFaceColorOperator)
    bpy.utils.unregister_tool(UVFaceColorPicker)
    bpy.utils.unregister_class(OPDrawColorPalette)
    bpy.types.IMAGE_MT_image.remove(image_menu_func)


if __name__ == "__main__":
    register()
