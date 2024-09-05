#version 330

in vec2 frag_uv;
out vec4 frag;

void main() {
    frag = vec4(vec3(.08, .1, .2) * frag_uv.x + vec3(.12, .05, .15) * frag_uv.y, 1.);
}
