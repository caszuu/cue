#version 330

// a simple built-in gizmo shader

layout(std140) uniform cue_camera_buf {
    mat4 bt_cam_mat;
};

layout(location = 0) in vec3 pos;
layout(location = 1) in vec3 col;

out vec3 frag_col;

void main() {
    gl_Position = bt_cam_mat * vec4(pos, 1.);
    frag_col = col;
}