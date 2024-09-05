#version 330

// a basic common hardcoded full screen triangle vs

vec4 verts[3] = vec4[3](
    vec4(-1, -1, 0, 1),
    vec4(-1, 5, 0, 1),
    vec4(5, -1, 0, 1)
);

out vec2 frag_uv;

void main() {
    gl_Position = verts[gl_VertexID % 3];
    frag_uv = (gl_Position.xy + 1) / 2; // remap from -1 to 1 to 0 to 1 range ideal for texture sampling
}