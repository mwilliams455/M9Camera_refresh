"""BODYQUAL1A: preserve thresholds and geometry; exclude invalid candidates before ranking."""
def one(s, old, new):
    n=s.count(old)
    if n!=1: raise ValueError(f'Expected one source anchor, got {n}: {old[:70]!r}')
    return s.replace(old,new,1)

def patch(source):
    start=source.index('    public static BodyCandidate multifieldBodyCandidate(Stats s) {')
    end=source.index('    private static int selectBodyBacklight(',start)
    method=source[start:end]
    marker='        BodyMetrics body=bodyMetrics(s,bestMask);'
    if method.count(marker)!=1: raise ValueError('Confidence section is not unique')
    prefix,tail=method.split(marker,1)
    prefix=one(prefix,
        '        int bestMask=0,bestCount=0;\n        double bestScore=0;',
        '        BodyCandidate bestCandidate=null;\n'
        '        boolean sawGeometricCandidate=false;\n'
        '        double bestScore=0;')
    prefix=one(prefix,
        '            double componentScore=sum*(1+.12*Math.min(count-1,4));\n'
        '            if(componentScore>bestScore) {\n'
        '                bestScore=componentScore;bestMask=mask;bestCount=count;\n'
        '            }',
        '            sawGeometricCandidate=true;\n'
        '            BodyCandidate candidate=bodyCandidateForComponent(s,mask,count);\n'
        '            if(!candidate.valid)continue;\n'
        '            double componentScore=sum*(1+.12*Math.min(count-1,4));\n'
        '            if(componentScore>bestScore) {\n'
        '                bestScore=componentScore;bestCandidate=candidate;\n'
        '            }')
    prefix=one(prefix,
        '        if(bestMask==0)return BodyCandidate.invalid("no_coherent_dark_body");\n\n',
        '        if(bestCandidate!=null)return bestCandidate;\n'
        '        return BodyCandidate.invalid(sawGeometricCandidate\n'
        '                ?"body_confidence_too_low":"no_coherent_dark_body");\n'
        '    }\n\n'
        '    private static BodyCandidate bodyCandidateForComponent(Stats s,int mask,int count) {\n')
    tail=tail.replace('bestMask,bestCount','mask,count')
    method=prefix+'        BodyMetrics body=bodyMetrics(s,mask);'+tail
    return source[:start]+method+source[end:]
