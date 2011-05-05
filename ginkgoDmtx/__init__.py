import numpy
import rs
# n0=numpy.array([[127,   0, 127, 127, 127, 127, 127,   0, 127,   0],
#        [  0,   0, 127, 127,   0,   0,   0, 127,   0,   0],
#        [127, 127, 127, 127, 127,   0,   0, 127, 127,   0],
#        [127,   0,   0, 127,   0,   0,   0,   0,   0, 127],
#        [  0, 127,   0,   0, 127, 127, 127, 127, 127, 127],
#        [  0,   0,   0, 127, 127,   0,   0,   0, 127, 127],
#        [127,   0,   0, 127, 127,   0,   0, 127,   0,   0],
#        [127,   0, 127,   0, 127,   0,   0, 127,   0,   0],
#        [127, 127, 127,   0, 127, 127, 127,   0, 127,   0],
#        [  0,   0, 127, 127,   0, 127,   0, 127,   0, 127]])
# #1013774809
# n=numpy.array([
# [1,0,1,1,1,1,1,0,1,0],
# [0,0,1,1,0,0,1,0,0,0],
# [1,1,1,0,0,1,1,1,1,0],
# [1,1,0,0,1,1,1,0,0,1],
# [0,1,0,0,0,1,0,1,1,0],
# [1,0,1,1,0,1,1,1,0,0],
# [1,0,0,1,1,0,0,1,0,1],
# [1,0,0,0,1,0,1,0,0,1],
# [1,1,1,0,0,1,0,1,1,0],
# [0,0,1,1,0,0,0,0,0,1]])

class ModuleECC200:
    def __init__(self,ndata = 5, ntotal = 12):
        self.rsDecoder=rs.RSCoder(ntotal,ndata)
        
    def getCodewords(self,dm):
        def norm(x,y):
            if x<0:
             #   print 10+x,y-2
                return 10+x,y-2
            if y<0:
                #print x-2,y+10
                return x-2,y+10
            return x,y

        def pick(dm,x,y):
            # note the reversal for numpy array format
            coord=norm(y,x)
            val = dm[coord]
            #print val,coord
            if int(val) == 0:
                return '0'
            else:
                return '1'

        def getByte(pos):
            #print pos
            x=pos[0]-2
            y=pos[1]-2
            s='0b'
    #        import pdb;pdb.set_trace()
            s+=pick(dm,x,y)
            s+=pick(dm,x+1,y)

            for j in range(2):
                for i in range(3):
                    s+=pick(dm,x+i,y+j+1)

#            print s
            return eval(s)

        slope = numpy.array([2,-2])
        position = numpy.array([0,4])
        reorient = numpy.array([3,1])
        codewords = []

        while 1:
            if (position < [10,10]).all() and (position >= [0,0]).all():
                codewords.append(getByte(position))

            if len(codewords) == 12:
                break
            elif position[1] < 0 or position[0] < 0:
                slope = -slope
                position += reorient
            if (position == [8,4]).all():
                slope = -slope
                position += [1, 3]
            else:
                position += slope


        return codewords


    def decode(self, matrix, debug = True):
        matrix = numpy.array(matrix)
        def mapping(x):
            if x >0 and x<129:
                return chr(x-1)
            elif x>129 and x<230:
                return str(x-130)
            elif x == 129:
                return ''#None
            else:
                print "unknown mapping"
                return ''#None

        cwords= self.getCodewords(matrix)

        if debug:
            print cwords

        data=self.rsDecoder.decode(str(bytearray(cwords)))

        if len(data) != 5:
            return None
        #data = data.replace('\x00','')
        #import pdb;pdb.set_trace()
        dlist = map(ord,data)

        if debug:
            print dlist
    
        decoded = map(mapping,dlist)
        
        printable = ''.join(map(lambda x: (len(x) == 1 and '0'+x) or x,decoded))
    
        if debug:
            print decoded
            print printable
        
        if len(printable) != 10 or printable[:2] != '10':
            return None
        return printable
