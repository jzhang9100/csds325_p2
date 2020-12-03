#!/usr/bin/python3
import socket
import time
import struct

DISCLAIMER_MESSAGE = "measurement for class project. questions to Jack Zhang cxz416@case.edu or professor mxr136@case.edu"
MAX_ATTEMPTS = 5
DATAGRAM_TTL = 64 #Recomended initial value from wikipedia
DEST_PORT = 33434
MAX_MSG_LEN = 1500
LOCAL_IP = '10.4.3.59' #via "ip r | grep default" command to get default local ip
UNEXPECTED_PACKET = "Recieved Packet From Unrelated Scource"

#Read target.txt and return a dict with {key=hostname val = hostip}
def read_targets():
    ret = {}
    for line in open('targets.txt'):
        name = line.rstrip()
        ret[name] = socket.gethostbyname(name)
    return ret

#Setup and return custom Datagram
def generate_datagram():
    ret = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.getprotobyname('udp'))
    ret.setsockopt(socket.SOL_IP, socket.IP_TTL, DATAGRAM_TTL)
    return ret

#Setup and return a Raw Socket
def generate_recv_socket():
    ret = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    ret.settimeout(5) #Using timeout instead of Poll/Select
    ret.bind(("", 0))
    return ret


def run():
    host_info = read_targets()
    
    #Datagram with custom values for probe (3)
    datagram = generate_datagram()
    #Raw socket to recieve ICMP messages (4)
    recv_socket = generate_recv_socket()
    #Create payload with DISCLAIMER_MESSAGE (5)
    payload = bytes(DISCLAIMER_MESSAGE + 'a'*(1472 - len(DISCLAIMER_MESSAGE)), 'ascii')

    RTT_info = {}
    hops_info = {}
    for item in host_info.items():
        host_name = item[0]
        host_ip = item[1]
        
        print("Testing: {}".format(host_name))        

        attempt = 0
        successful_send = False
        while attempt < MAX_ATTEMPTS and not successful_send:
            try:
                #Send Packet
                packet_send_time = time.time()
                datagram.sendto(payload, (host_ip, DEST_PORT))
                
                #Recieve Packet
                response = recv_socket.recv(MAX_MSG_LEN)    
                packet_response_time = time.time() 
    
                #Read ICMP Packet Response Information
                source_ip = socket.inet_ntoa(response[12:16])
                dest_ip = socket.inet_ntoa(response[16:20])
                
                response_source_ip = socket.inet_ntoa(response[40:44])
                response_dest_ip = socket.inet_ntoa(response[44:48])
                
                dest_port = struct.unpack("!H", response[50:52])[0]

                #Implement 3 techniques from (6) to check that we didnt recienve unrelated packets (NOTE: MIsha say IPID no work so just other 2 techniques)
                if((source_ip != host_ip or response_dest_ip != host_ip) or (dest_ip != LOCAL_IP or response_source_ip != LOCAL_IP)):
                    print(UNEXPECTED_PACKET)
                    raise socket.error
                
                #Measure RTT
                RTT = 1000 * (packet_response_time - packet_send_time)
                RTT_info[host_name] = RTT
                
                #Measure Hops
                R_TTL = response[36]
                hops = DATAGRAM_TTL - R_TTL
                hops_info[host_name] = hops
                successful_send = True                
                print("Bytes Recieved: {} \nRTT: {} ms \nHop Count: {}".format(len(response[28:]), RTT, hops))

            except socket.error:
                print("Attempt #{} failed for hostname: {}".format(attempt, host_name))
                attempt += 1
        if not successful_send:
            print("Timed Out")
        print("\n\n" + 30*'-' + "\n\n")            
        time.sleep(2)
    datagram.close()
    recv_socket.close()


    #Plot data and save graph
    import matplotlib.pyplot as plt
    points = []
    assert hops_info.keys() == RTT_info.keys()

    #create tuples of RTTs to coresponding Hop Counts
    for key in hops_info.keys():        
        tup = (RTT_info[key], hops_info[key])
        points.append(tup)
        plt.annotate(key, tup, textcoords='offset points', xytext=(0,5), ha='center')
        
    #plot points
    plt.scatter(*zip(*points))

    plt.title('RTT vs Hop Count')
    plt.xlabel('RTT (ms)')
    plt.ylabel('Hop Count')
    plt.savefig('figures/hops_vs_RTT.png')

if __name__ == "__main__":
    run()
