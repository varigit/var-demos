# Start from nodejs container with Alpine Linux
FROM node:18-alpine

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
# A wildcard is used to ensure both package.json AND package-lock.json are copied
# where available (npm@5+)
COPY package*.json ./

# Install node package manager
RUN npm install

# Install python/pip
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

# Install socat
RUN apk add --update socat

# Install Python libgpiod library
RUN pip3 install gpiod

# Copy in contents of our app directory
COPY . .

EXPOSE 8080
CMD [ "sh", "start-demo-services.sh" ]
