#version 330

// a basic common hardcoded full screen triangle vs

vec4 verts[3] = vec4[3](
    vec4(0, -.5, .2, 1),
    vec4(-.5, .5, .5, 1),
    vec4(.5, .5, .5, 1)
);

vec3 cols[3] = vec3[3](
    vec3(1, 0, 0),
    vec3(0, 1, 0),
    vec3(0, 0, 1)
);

layout(std140) uniform cue_camera_buf {
    mat4 bt_cam_mat;
};

uniform mat4 cue_model_mat;

out vec2 frag_uv;
out vec3 frag_col;

void main() {
    gl_Position = bt_cam_mat * cue_model_mat * verts[gl_VertexID % 3];
    frag_uv = (gl_Position.xy + 1) / 2; // remap from -1 to 1 to 0 to 1 range ideal for texture sampling
    frag_col = cols[gl_VertexID % 3];
    // frag_col = vec3(gl_Position.zw, 0);
}
