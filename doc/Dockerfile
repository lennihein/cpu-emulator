FROM archlinux/archlinux:base-devel

# install git
RUN pacman -Syyu git doas --noconfirm --needed

# add user lenni with sudo and doas permits
RUN useradd -g wheel -m theuser\
    && echo "%wheel ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers\
    && echo "permit nopass :wheel" >> /etc/doas.conf
USER theuser
WORKDIR /home/theuser

# install paru (and change AUR-order to descending)
RUN git clone https://aur.archlinux.org/paru.git && cd paru && makepkg -si --noconfirm && cd ../ && rm paru -rf

# mount doc folder
VOLUME ["/doc"]
WORKDIR /doc

# install required packages
RUN paru -S pandoc pandoc-crossref mkpdf texlive-most biber --noconfirm --needed -y

# add biber to path
ENV PATH="/usr/bin/site_perl:/usr/bin/vendor_perl:/usr/bin/core_perl:${PATH}"

# compile markdown -> latex -> pdf
CMD [ "/doc/build.sh" ] 