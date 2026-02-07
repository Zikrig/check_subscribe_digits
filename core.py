def cor(a):
    i = 0
    while a > 0:
        d = a % 10
        a = a // 10
        i += d
    
    return i

def corfull(a):
    while a > 10:
        a = cor(a)
    return a

def ost(a):
    return (a+5) % 10

ii = [corfull(i) for i in range(100)]
ii.sort()
print(ii)

jj = [ost(i) for i in range(100)]

jj.sort()
print(jj)