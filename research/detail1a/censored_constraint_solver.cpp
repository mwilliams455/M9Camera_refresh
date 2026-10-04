// Offline rejected reconstruction probe. This is a TV prior, not M9 firmware.
// Unsaturated CFA values are equalities, saturated values are lower bounds.
// Objective: TV(G) + chroma * (TV(R-G) + TV(B-G)), anisotropic forward TV.
// Fixed iteration count; no optimality/convergence certificate is claimed.
#include <algorithm>
#include <vector>

extern "C" void solve(const double* data, const unsigned char* channel,
    const unsigned char* clipped, const double* init, int w, int h,
    int iterations, double chroma, double* output) {
    int n = w*h;
    std::vector<double> u(init, init+3*n), bar=u, next(u.size()), p(6*n, 0.);
    auto project = [&](std::vector<double>& z) {
        for (int i=0; i<n; i++) {
            int k=3*i+channel[i];
            z[k]=clipped[i] ? std::max(data[i], z[k]) : data[i];
            for (int c=0; c<3; c++) z[3*i+c]=std::max(0., z[3*i+c]);
        }
    };
    project(u); bar=u;
    constexpr double step=.16;
    for (int t=0; t<iterations; t++) {
        for (int y=0; y<h; y++) for (int x=0; x<w; x++) {
            int i=y*w+x;
            double v[3]={bar[3*i+1], bar[3*i]-bar[3*i+1], bar[3*i+2]-bar[3*i+1]};
            for (int a=0; a<2; a++) {
                int j=i+(a?w:1);
                bool edge=a ? y==h-1 : x==w-1;
                double q[3]={0., 0., 0.};
                if (!edge) {
                    q[0]=bar[3*j+1]-v[0];
                    q[1]=bar[3*j]-bar[3*j+1]-v[1];
                    q[2]=bar[3*j+2]-bar[3*j+1]-v[2];
                }
                for (int c=0; c<3; c++) {
                    int k=6*i+3*a+c;
                    double bound=c ? chroma : 1.;
                    p[k]=edge ? 0. : std::clamp(p[k]+step*q[c], -bound, bound);
                }
            }
        }
        for (int y=0; y<h; y++) for (int x=0; x<w; x++) {
            int i=y*w+x;
            double adj[3];
            for (int c=0; c<3; c++)
                adj[c]=-p[6*i+c]-p[6*i+3+c]+(x?p[6*(i-1)+c]:0.)+(y?p[6*(i-w)+3+c]:0.);
            next[3*i]=u[3*i]-step*adj[1];
            next[3*i+1]=u[3*i+1]-step*(adj[0]-adj[1]-adj[2]);
            next[3*i+2]=u[3*i+2]-step*adj[2];
        }
        project(next);
        for (int i=0; i<3*n; i++) bar[i]=2*next[i]-u[i];
        u.swap(next);
    }
    std::copy(u.begin(), u.end(), output);
}
