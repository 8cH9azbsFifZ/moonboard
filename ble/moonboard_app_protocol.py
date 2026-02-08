import logging
import string

X_GRID_NAMES = string.ascii_uppercase[0:11]

def position_trans(p,num_rows):
    """convert led number (strip number) to moonboard grid """
    col= p//num_rows
    row= (p%num_rows) +1
    if col%2==1:
        row=(num_rows+1)-row
    return X_GRID_NAMES[col]+str(row)
    
def decode_problem_string(s, flags):
    holds = {
        'START':[],
        'MOVES':[],
        'LEFT':[],
        'FOOT':[],
        'MATCH':[],
        'TOP':[], 
        'FLAGS':flags}

    if "M" in  flags:
        num_rows = 12
    else:
        num_rows = 18
    
    if "B" in  flags:
        colors = True
    else:
        colors = False

    for h in s.split(','):
        try:
            t = h[0]
            p = position_trans(int(h[1:]), num_rows)
        except Exception as X:
            #error in decoding show red led in A1
            t = "E"
            p = "A1"
        
        if t=='S':
            holds['START'].append(p)
        if colors: 
            if t=='L':
                holds['LEFT'].append(p)
            if t=='F':
                holds['FOOT'].append(p)
            if t=='M':
                holds['MATCH'].append(p)
            if t=='R':
                holds['MOVES'].append(p)
        elif t=='P' or t == 'R' or t == 'L' or t == 'M' or t =='F':
            holds['MOVES'].append(p)
        if t=='E':
            holds['TOP'].append(p)
    return holds

class UnstuffSequence():
    """
    hold sequence come separated in parts due to BLE packet size limitation
    this class serves to put different parts together
    """
    START = 'l#'
    STOP= '#'

    def __init__(self,logger=None):
        if logger is None:
            self.logger= logging
        else:
            self.logger=logger
        self.s=''
        self.flags=[]

    def process_bytes(self, ba):
        """ 
        process new incoming bytes and return if new problem is available. 
        handle some error due to multiple connected devices sending simoultaneously.
        """

        s = bytearray.fromhex(ba).decode(errors="ignore")
        self.logger.debug("incoming bytes:"+str(s))
        
        if s[0] == '~':
            """
            if the string begins with ~  means that there are flags
            the legend is: 
            M = mini board
            D = duble led above and below holds
            B = colors and use start left right foot end match
            """
            s = s[1:]
            self.flags.append(s[0])
            s = s[1:]
            if s[0] == '*':
                s = s[1:]
            else:
                s = s[1:]
                self.flags.append(s[0])
                s = s[1:]
                s = s[1:]

        if s[:2]==self.START:
            self.logger.debug('START')
            if self.s =='':
                if s[-1]==self.STOP:
                    return s[2:-1]
                else:
                    self.s=s[2:]
            else:
                self.logger.debug('error: alredy started')
                self.s= ''
        elif s[-1]==self.STOP:
            self.logger.debug('STOP')
            if self.s!='':
                ret = self.s+s[:-1]
                self.s=''
                return ret
            else:
                self.logger.debug('error: not started')
                self.s= ''
        else:
            self.s+=s
