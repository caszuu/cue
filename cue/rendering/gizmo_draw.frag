#version 330

// a simple built-in gizmo shader

in vec3 frag_col;
out vec4 frag;

void main() {
    frag = vec4(frag_col, 1.);
}