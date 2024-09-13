#version 330

in vec3 frag_col;
out vec4 frag;

void main() {
    frag = vec4(frag_col, 1.);
}
