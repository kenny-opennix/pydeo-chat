import re, sys, time, socket, Queue
import pygame, pygame.camera
from pygame.locals import *
from threading import Thread
# TODOs:
# implement handshake
# implement avatars
# need smooth exit
# handle dropped connection
# implement audio
# handle multiple connections

# ******************************
# Global vars
# ******************************
q                = Queue.Queue() # queue to hold send images
ips              = []            # all ips in local network for which there is no connection
run              = True          # threads will run so long as this is True
port             = 9000          # port for all sockets
size             = (640,480)     # size of images and display
img_len          = 1228800       # length of a tostring'd image
send_connections = []            # array of ips to send images to


# ******************************
# Thread defs
# ******************************

# Thread to queue up images
def snapshots():
    global q, run, cam, surface_send
    
    while run:
        # take an image
        img = cam.get_image(surface_send)
        # ensure it's the correct size
        img = pygame.transform.scale(img, size)
        # tostring it
        img_str = pygame.image.tostring(img,'RGBX')
        # add delimiters
        img_data = '@@start@@'+img_str+'@@end@@'
        # don't let the queue get too big
        if q.qsize() == 20: q.get()
        # put the image in the queue
        q.put(img_data)
        time.sleep(0)

    print 'exiting snapshots thread'
    return

# Thread to accept socket connections and create recv_threads
def accept_connections():
    global run
    
    # create the listening server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((socket.gethostname(),port))
    server.listen(5)
    
    while run:
        # accept a connection
        recv_socket, address = server.accept()
        # create a recv_thread for the connection
        Thread(target=recv_thread, args=(recv_socket, address[0], )).start()
        time.sleep(0)

    print 'exiting accept_connections thread'
    return

# Thread to recv data from a socket connection
def recv_thread(recv_socket, ip):
    global run, ips, size, port, display, img_len
    
    #recv_size = 614408      # set the recv size
    pack_size = 1228816     # pack size is the expected size of the recv image string with delimiters
    recv_size = pack_size
    print 'recv_thread started for', ip
    
    # if a send_thread has not been established with this ip, create it here
    if ip in ips:
        # remove the ip so that a send_thread creation to this ip is not attempted elsewhere
        ips.remove(ip)
        
        # create send_socket
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_socket.settimeout(5)
        try:
            # create the send_thread
            send_socket.connect((ip,port))
            Thread(target=send_thread, args=(send_socket,ip,'recv_thread', )).start()
        except:
            print 'recv_thread tried starting a send_thread with', ip, 'but was unsuccessful'
            send_socket.close()
    
    while run:
        msg = ''
        # recv a msg until pack_size is reached
        while len(msg) != pack_size:
            msg += recv_socket.recv(recv_size)
            # adjust recv_size for next iteration
            recv_size = pack_size - len(msg)
        
        print 'msg received'
        # msg has been recv'd, reset recv_size
        recv_size = pack_size
        
        # debuggin'
        print 'First 9:', msg[0:9]
        print 'Last 7:', msg[-7:]
        # end debuggin'
        
        # check if msg has delimiters
        if re.search('@@start@@', msg) and re.search('@@end@@',msg):
            # strip delimiters
            img_str = msg.split('@@start@@')[1]
            img_str = img_str.split('@@end@@')[0]
            
            # check if img_str has correct length
            if len(img_str) == img_len:
                # convert img_str to surface 
                recv_img = pygame.image.frombuffer(img_str,size,'RGBX')
                # display the received image
                display.blit(recv_img,(0,0))
                pygame.display.update()
                time.sleep(0)

    print 'exiting recv_thread'
    # close the socket before returning
    recv_socket.close()
    return

# Thread to send data to a socket connection
def send_thread(send_socket, ip, debug_src):
    global q, run
    
    print 'send_thread started for', ip, 'from', debug_src
    
    # set the connection timeout
    send_socket.settimeout(60)
    while run:
        # get an img_str from the queue
        img_str = q.get()
        try:
            # send all img_str
            sent = 0
            while sent != len(img_str):
                sent += send_socket.send(img_str)
            print 'TOTAL SENT:', str(sent)
        except:
            print 'ERROR IN SEND!'
            continue

    print 'exiting send_thread'
    # close the socket before returning
    send_socket.close()
    return

# ******************************
# Main
# ******************************

# initialize pygame stuff
pygame.init()
pygame.camera.init()
camlist = pygame.camera.list_cameras()

if camlist:
    # create surfaces and start camera
    display = pygame.display.set_mode(size, 0)
    surface_send = pygame.surface.Surface(size, 0)
    surface_recv = pygame.surface.Surface(size, 0, display)
    cam = pygame.camera.Camera(camlist[0], size)
    cam.start()
else:
    print 'camera not found!'
    sys.exit()


# create ips array
# using 10-20 for testing
for i in range(10,20):
#for i in range(1,255):
    ip = '192.168.0.%s' % i
    if not ip == socket.gethostbyname(socket.gethostname()):
        ips.append(ip)

# start thread to take snapshots
Thread(target=snapshots, ).start()

# start thread to accept connections
Thread(target=accept_connections, ).start()

# start send threads
while run:
    try:
        for ip in ips:
            send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_socket.settimeout(5)
            try:
                send_socket.connect((ip,port))
            except:
                continue
            ips.remove(ip)
            Thread(target=send_thread, args=(send_socket, ip, 'main', )).start()
    except KeyboardInterrupt:
        print 'setting run to False'
        run = False
    time.sleep(0)

pygame.quit()
sys.exit()