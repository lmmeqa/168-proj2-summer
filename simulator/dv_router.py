"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.
        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####
        self.history = {}
        self.reset_history()
        ##### End Stage 10A #####
    def reset_history(self):
        self.history = {}
    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        self.table[host] = TableEntry(dst = host, port = port, latency = self.ports.get_latency(port), expire_time=FOREVER)

        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """

        ##### Begin Stage 2 #####
        host = packet.dst
        if host not in self.table:return
        port = self.table[packet.dst].port
        if self.table[packet.dst].latency >= INFINITY:return
        self.send(packet, port=port)
        ##### End Stage 2 #####


    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        to_send = []

        if force:
            self.reset_history()
        ports = [single_port] if single_port is not None else self.ports.get_all_ports()
        for port in ports:
            for host, entry in self.table.items():
                latency = min(INFINITY, entry.latency)
                if entry.port == port:
                    if self.POISON_REVERSE:
                        latency = INFINITY
                        
                    if self.SPLIT_HORIZON:
                        continue
                last_advertised = self.history.get((port, host))
                if force or last_advertised != latency:
                    self.send_route(port, host, latency)
                    self.history[(port, host)] = latency
    #### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        table = self.table
        ports = self.ports
        expired = []
        for host, entry in table.items():
            if entry.has_expired:
                expired+=[host]
        for expiree in expired:
            if self.POISON_EXPIRED:
                table[expiree] = TableEntry(dst=expiree, port=table[expiree].port, latency=INFINITY, expire_time=api.current_time()+self.ROUTE_TTL)
                continue
            table.pop(expiree)
            self.s_log("%s's route expired and was removed from router's forwarding table", expiree.name)

        ##### End Stages 5, 9 #####




    def addEntry(self, route_dst, route_latency, port):
        table = self.table
        ports = self.ports
        table[route_dst] = TableEntry(dst=route_dst, port=port, latency=ports.get_latency(port) + route_latency, expire_time= api.current_time() + self.ROUTE_TTL)
    
    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        table, ports = self.table, self.ports
        if route_dst not in table:
            self.addEntry(route_dst, route_latency, port)
        else:
            entry = table[route_dst]
            new_cost = ports.get_latency(port) + route_latency
            if new_cost < entry.latency:
                self.addEntry(route_dst, route_latency, port)
            elif port == entry.port and new_cost != entry.latency:
                self.addEntry(route_dst, route_latency, port)
        
        self.send_routes()
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####
        if self.SEND_ON_LINK_UP:
            self.send_routes(force=True, single_port=port)
        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####

        for host, table in self.table.items():
            if table.port == port:
                if self.POISON_ON_LINK_DOWN:
                    self.table[host] = TableEntry(dst=host, port=table.port, latency=INFINITY, expire_time=api.current_time()+self.ROUTE_TTL)



        self.send_routes()
        ##### End Stage 10B #####

    # Feel free to add any helper methods!
